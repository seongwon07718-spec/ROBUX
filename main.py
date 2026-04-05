import hashlib
import base64
import time
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class RobloxAPI:
    def __init__(self, cookie=None):
        self.session = requests.Session()
        self.session.headers.update(self.BASE_HEADERS)
        if cookie:
            clean = cookie.strip()
            if "=" in clean:
                clean = clean.split("=", 1)[-1]
            self.session.cookies.set(".ROBLOSECURITY", clean, domain=".roblox.com")
        # ✅ ECDSA 키 생성
        self.private_key = ec.generate_private_key(
            ec.SECP256R1(), default_backend()
        )

    def generate_bat(self, url: str, body: str = "") -> str:
        """x-bound-auth-token 생성"""
        body_hash = base64.b64encode(
            hashlib.sha256(body.encode()).digest()
        ).decode()
        timestamp = str(int(time.time()))
        message = f"{body_hash}\n{timestamp}".encode()
        signature = self.private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        sig_b64 = base64.b64encode(signature).decode()
        return f"v1|{body_hash}|{timestamp}|{sig_b64}"

    def buy_gamepass(self, pass_id: int) -> dict:
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}

        price = int(info.get("PriceInRobux") or 0)
        token = self.get_csrf_token()
        if not token:
            return {"purchased": False, "reason": "CSRF 토큰 획득 실패"}

        url = f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/purchase"
        body = json.dumps({"expectedPrice": price})

        # ✅ BAT 토큰 생성
        bat = self.generate_bat(url, body)

        headers = {
            "x-csrf-token": token,
            "Content-Type": "application/json",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com",
            "x-bound-auth-token": bat,
        }

        resp = self.session.post(url, data=body, headers=headers)
        print(f"[구매결과] status={resp.status_code} body={resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}
