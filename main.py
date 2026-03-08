import json
import os
import urllib.request
import urllib.error
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# --- 1. 서버 설정 (아이폰 신호를 받는 부분) ---
app = FastAPI()

class ChargeData(BaseModel):
    message: str

@app.post("/charge")
async def receive_charge(data: ChargeData):
    """아이폰 단축어에서 보낸 메시지를 여기서 받습니다."""
    print(f"📥 입금 문자 수신: {data.message}")
    # 여기에 데이터베이스 업데이트나 봇 알림 로직을 추가할 수 있습니다.
    return {"ok": True, "message": "성공적으로 수신됨"}

# --- 2. 클라이언트 설정 (봇이 서버에 물어볼 때 쓰는 부분) ---
_port = os.getenv("CHARGE_API_PORT", "88")
_default_url = f"http://127.0.0.1:{_port}/"
# 실제 서비스 주소는 Cloudflare 주소로 설정되어야 합니다.
CHARGE_API_URL = os.getenv("CHARGE_API_URL", "https://pay.rbxshop.cloud").strip()
TIMEOUT_SEC = int(os.getenv("CHARGE_CLIENT_TIMEOUT", "15"))

def send_charge_message(message: str) -> dict:
    """봇(main.py)이 이 함수를 호출하여 입금 내역이 있는지 확인합니다."""
    url = CHARGE_API_URL.rstrip("/") + "/charge"
    
    payload = {"message": (message or "").strip()}
    if not payload["message"]:
        return {"ok": False, "error": "메시지가 비어 있음"}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    try:
        # 이 부분은 실제 입금 DB와 대조하는 로직으로 대체되거나 
        # 위 receive_charge에서 저장한 데이터를 확인하는 방식으로 작동해야 합니다.
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            data = res.read().decode("utf-8")
            out = json.loads(data) if data.strip() else {}
            return {
                "ok": out.get("ok", False),
                "error": out.get("error"),
                "duplicate": out.get("duplicate"),
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    
# --- 3. 실행 부분 ---
if __name__ == "__main__":
    # 이제 uvicorn이 app을 인식하여 88번 포트에서 서버를 시작합니다.
    print(f"🚀 iOS 자동충전 서버를 시작합니다... (Port: 88)")
    uvicorn.run(app, host="0.0.0.0", port=88)
