from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, field_validator
import sqlite3
import os
import re
import hmac
import hashlib
import secrets
from datetime import datetime

# ── 설정 ──────────────────────────────────────────────
DB_DIR         = "DB"
WEBHOOK_SECRET = "f1356103e6b861cb00d3c502cb27d9f66bd84880f70d3b98186fdbd5cd1d840c"
ALLOWED_DOMAIN = "여기에_도메인_입력"   # 예: yourdomain.com
# ──────────────────────────────────────────────────────

# Cloudflare 사용 시 TrustedHostMiddleware 제거
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Rate limit (IP당 분당 30회)
_rate_limit_store: dict[str, list] = {}

def rate_limit_check(ip: str, limit: int = 30, window: int = 60) -> bool:
    now = datetime.now().timestamp()
    hits = _rate_limit_store.get(ip, [])
    hits = [t for t in hits if now - t < window]
    if len(hits) >= limit:
        return False
    hits.append(now)
    _rate_limit_store[ip] = hits
    return True


# ── DB 헬퍼 ───────────────────────────────────────────

def get_guild_db_path_by_id(guild_id: str) -> str | None:
    for fname in os.listdir(DB_DIR):
        if not fname.endswith(".db") or fname == "라이센스.db":
            continue
        path = os.path.join(DB_DIR, fname)
        try:
            with sqlite3.connect(path) as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM info WHERE guild_id = ?", (guild_id,))
                if c.fetchone():
                    return path
        except Exception:
            continue
    return None

def get_shortcut_token(guild_id: str, db_path: str) -> str | None:
    """서버 DB에서 shortcut_token 조회"""
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT shortcut_token FROM info WHERE guild_id=?", (guild_id,))
            row = c.fetchone()
            return row[0] if row and row[0] else None
    except Exception:
        return None


# ── SMS 파싱 ──────────────────────────────────────────

def parse_kakaobank_sms(sms: str) -> tuple[str, int] | None:
    """
    카카오뱅크 입금 알림 문자 파싱
    형식:
    [Web발신]
    [카카오뱅크]
    정*원(3823)
    04/27 23:19
    입금 100원
    정성원
    잔액 300원
    """
    # 카카오뱅크 문자인지 확인
    if "[카카오뱅크]" not in sms:
        return None

    lines = [line.strip() for line in sms.strip().splitlines() if line.strip()]

    # 입금 금액 추출: "입금 100원" 형식
    amount = None
    depositor = None

    for i, line in enumerate(lines):
        # 금액 라인: "입금 숫자원"
        amount_match = re.search(r"입금\s+([\d,]+)원", line)
        if amount_match:
            amount_str = amount_match.group(1).replace(",", "")
            try:
                amount = int(amount_str)
            except ValueError:
                return None

            # 입금자명은 금액 라인 다음 라인
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # 잔액 라인이 아닌지 확인
                if not re.search(r"잔액", next_line):
                    depositor = next_line.strip()
            break

    if not amount or not depositor:
        return None

    # 입금자명 유효성: 한글/영문/숫자 1~20자
    if not re.fullmatch(r"[가-힣a-zA-Z0-9]{1,20}", depositor):
        return None

    if amount <= 0 or amount > 10_000_000:
        return None

    return depositor, amount


# ══════════════════════════════════════════════════════
# iOS 단축어 → SMS 웹훅
# ══════════════════════════════════════════════════════

class SmsWebhookPayload(BaseModel):
    token: str       # 서버별 shortcut_token (DB에서 검증)
    guild_id: str    # 디스코드 서버 ID
    sms_body: str    # 카카오뱅크 입금 알림 문자 원문

    @field_validator("guild_id")
    @classmethod
    def validate_guild_id(cls, v):
        if not re.fullmatch(r"\d{17,20}", v):
            raise ValueError("잘못된 guild_id")
        return v

    @field_validator("sms_body")
    @classmethod
    def validate_sms_body(cls, v):
        if len(v) > 500:
            raise ValueError("문자 내용이 너무 깁니다")
        return v

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v):
        # token은 hex 48자 (secrets.token_hex(24))
        if not re.fullmatch(r"[0-9a-f]{48}", v):
            raise ValueError("잘못된 토큰 형식")
        return v


@app.post("/webhook/sms")
async def sms_webhook(payload: SmsWebhookPayload, request: Request):
    # Rate limit
    client_ip = request.client.host
    if not rate_limit_check(client_ip, limit=30, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    # 서버 DB 찾기
    db_path = get_guild_db_path_by_id(payload.guild_id)
    if not db_path:
        raise HTTPException(status_code=404, detail="서버를 찾을 수 없습니다")

    # 서버별 shortcut_token 검증 (DB에서 조회)
    stored_token = get_shortcut_token(payload.guild_id, db_path)
    if not stored_token:
        raise HTTPException(status_code=401, detail="단축어 토큰이 발급되지 않았습니다")
    if not hmac.compare_digest(stored_token, payload.token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # SMS 파싱
    parsed = parse_kakaobank_sms(payload.sms_body)
    if not parsed:
        raise HTTPException(status_code=400, detail="카카오뱅크 입금 알림 형식이 아닙니다")

    depositor, amount = parsed

    # 대기 중인 충전 찾기 (입금자명 + 금액 일치)
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT charge_id, user_id, depositor, amount
            FROM charge_pending
            WHERE status='pending' AND depositor=? AND amount=?
            ORDER BY created_at ASC
            LIMIT 1
        """, (depositor, amount))
        row = c.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="일치하는 충전 대기가 없습니다")

    charge_id = row[0]

    # 봇 웹훅 핸들러 호출 (HMAC 서명 생성)
    from bot import bot as discord_bot
    body = f"{charge_id}:{depositor}:{amount}:{payload.guild_id}".encode()
    sig  = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

    success = await discord_bot.handle_charge_webhook(
        charge_id=charge_id,
        depositor=depositor,
        amount=amount,
        guild_id=payload.guild_id,
        signature=sig,
        raw_body=body
    )

    if not success:
        raise HTTPException(status_code=400, detail="충전 처리 실패")

    return {"status": "ok", "charge_id": charge_id, "amount": amount, "depositor": depositor}


# ══════════════════════════════════════════════════════
# 단축어 설정 가이드
# ══════════════════════════════════════════════════════

@app.get("/shortcut/guide")
async def shortcut_guide(token: str, guild_id: str, request: Request):
    client_ip = request.client.host
    if not rate_limit_check(client_ip, limit=10, window=60):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    if not re.fullmatch(r"\d{17,20}", guild_id):
        raise HTTPException(status_code=400, detail="잘못된 guild_id")

    db_path = get_guild_db_path_by_id(guild_id)
    if not db_path:
        raise HTTPException(status_code=404, detail="서버를 찾을 수 없습니다")

    stored_token = get_shortcut_token(guild_id, db_path)
    if not stored_token or not hmac.compare_digest(stored_token, token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "guide": "iOS 단축어 설정 방법",
        "steps": [
            "1. iPhone 단축어 앱 > 자동화 > 새 자동화",
            "2. 메시지 수신 선택",
            "3. 보낸 사람: 카카오뱅크 (발신 번호 추가)",
            "4. 동작 추가: URL 가져오기",
            f"5. URL: https://{ALLOWED_DOMAIN}/webhook/sms",
            "6. 방법: POST / 헤더: Content-Type = application/json",
            f"7. 본문(JSON): {{\"token\": \"{token}\", \"guild_id\": \"{guild_id}\", \"sms_body\": \"[단축어 변수: 수신된 메시지 내용]\"}}",
            "8. 백그라운드에서 실행 활성화",
            "9. 실행 전 묻기 비활성화"
        ],
        "sms_example": "[Web발신]\n[카카오뱅크]\n정*원(3823)\n04/27 23:19\n입금 10,000원\n홍길동\n잔액 50,000원"
    }


# ══════════════════════════════════════════════════════
# 헬스체크
# ══════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
