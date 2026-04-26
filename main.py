import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ── CORS 설정 ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 인증코드 임시 저장 (메모리) ──
code_store: dict = {}

# ── Gmail 설정 (.env에서 불러옴) ──
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PW = os.getenv("GMAIL_APP_PW")

# ── HTML 파일 경로 (server.py 와 같은 폴더에 있어야 함) ──
HTML_PATH = Path(__file__).parent / "ott_final.html"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 요청/응답 모델
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SendCodeRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이메일 발송 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_email(to_email: str, code: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[OTT 최상급] 이메일 인증 코드"
    msg["From"] = GMAIL_USER
    msg["To"] = to_email

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans KR',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 20px;">
        <tr>
          <td align="center">
            <table width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
              <tr>
                <td style="background:#2563eb;padding:32px;text-align:center;">
                  <p style="margin:0;font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;">OTT 최상급</p>
                  <p style="margin:8px 0 0;font-size:13px;color:rgba(255,255,255,0.75);">프리미엄 구독 서비스</p>
                </td>
              </tr>
              <tr>
                <td style="padding:36px 32px;">
                  <p style="margin:0 0 8px;font-size:20px;font-weight:700;color:#0f172a;">이메일 인증 코드</p>
                  <p style="margin:0 0 28px;font-size:14px;color:#64748b;line-height:1.6;">
                    아래 6자리 인증 코드를 입력해주세요.<br>코드는 <strong>5분간</strong> 유효합니다.
                  </p>
                  <div style="background:#f1f5f9;border-radius:14px;padding:24px;text-align:center;margin-bottom:28px;">
                    <p style="margin:0;font-size:42px;font-weight:900;color:#2563eb;letter-spacing:12px;">{code}</p>
                  </div>
                  <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.6;">
                    본인이 요청하지 않았다면 이 이메일을 무시해주세요.<br>
                    인증 코드는 타인에게 공유하지 마세요.
                  </p>
                </td>
              </tr>
              <tr>
                <td style="background:#f8fafc;padding:20px 32px;text-align:center;border-top:1px solid #e2e8f0;">
                  <p style="margin:0;font-size:12px;color:#94a3b8;">© 2025 OTT 최상급. All rights reserved.</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PW)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTML 서빙
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/", response_class=HTMLResponse)
def serve_html():
    if not HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="ott_final.html 파일을 server.py 와 같은 폴더에 놓아주세요.")
    return HTMLResponse(content=HTML_PATH.read_text(encoding="utf-8"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API 엔드포인트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/health")
def health():
    return {"status": "OTT 최상급 서버 정상 동작 중"}


@app.post("/send-code")
def send_code(req: SendCodeRequest):
    code = "".join(random.choices(string.digits, k=6))
    expires = datetime.now() + timedelta(minutes=5)
    code_store[req.email] = {"code": code, "expires": expires}

    try:
        send_email(req.email, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {str(e)}")

    return {"message": "인증 코드가 발송되었습니다."}


@app.post("/verify-code")
def verify_code(req: VerifyCodeRequest):
    stored = code_store.get(req.email)

    if not stored:
        raise HTTPException(status_code=400, detail="인증 코드를 먼저 요청해주세요.")

    if datetime.now() > stored["expires"]:
        del code_store[req.email]
        raise HTTPException(status_code=400, detail="인증 코드가 만료되었습니다. 다시 요청해주세요.")

    if stored["code"] != req.code:
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다.")

    del code_store[req.email]
    return {"message": "인증 성공!", "email": req.email}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# python server.py 로 바로 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
