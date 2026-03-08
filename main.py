import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# 설정값 로드
_port = os.getenv("CHARGE_API_PORT", "88")
_default_url = f"http://127.0.0.1:{_port}/"
CHARGE_API_URL = os.getenv("CHARGE_API_URL", _default_url).strip() or _default_url
TIMEOUT_SEC = int(os.getenv("CHARGE_CLIENT_TIMEOUT", "15"))

def send_charge_message(message: str) -> dict:
    """API 서버에 충전 메시지를 전송하고 결과를 반환합니다."""
    url = CHARGE_API_URL.rstrip("/")
    if not url.startswith("http"):
        url = "http://" + url
    if not url.endswith("/") and "/charge" not in url:
        url = url + "/"

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
