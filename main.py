import aiohttp
import asyncio

class Pin:
    def __init__(self, pin_string):
        # 핀번호에서 하이픈 제거 및 공백 정리
        self.pin = pin_string.replace("-", "").strip()
        self.amount = 0
        self.message = "미처리"

class Cultureland:
    def __init__(self):
        # 반드시 언더바 2개(__)가 붙은 __init__ 이어야 합니다.
        self.session = None
        self.base_url = "https://m.cultureland.co.kr"

    async def login(self, cookie):
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/csh/cshGiftCardCfrm.do",
            "Origin": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        # SSL 인증서 오류 방지를 위해 connector 설정 추가
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(headers=headers, connector=connector)

    async def charge_process(self, pins):
        if not self.session:
            return pins[0] if pins else None

        # 최신 충전 확인 API 경로
        url = f"{self.base_url}/csh/cshGiftCardCfrm.do"
        target = pins[0]
        
        # 핀번호 전송 데이터 (Payload)
        payload = {
            "txt_pin_no": target.pin,
            "is_scms": "N",
            "scrId": "MT0101"
        }

        try:
            # allow_redirects=False로 설정하여 로그인이 풀렸을 때 튕기도록 함
            async with self.session.post(url, data=payload, timeout=10, allow_redirects=False) as resp:
                # 응답이 HTML(로그인 페이지)이면 세션 만료로 판단
                if resp.status == 302 or "text/html" in resp.headers.get("Content-Type", ""):
                    target.amount = 0
                    target.message = "로그인 세션 만료 (쿠키 갱신 필요)"
                    return target

                data = await resp.json()
                result_code = str(data.get("result", ""))
                
                if result_code == "0" or "성공" in data.get("resultMsg", ""):
                    target.amount = int(data.get("chargeAmount", 0))
                    target.message = "성공"
                else:
                    target.amount = 0
                    target.message = data.get("resultMsg", "잘못된 핀번호입니다")
        except Exception as e:
            target.amount = 0
            target.message = f"오류 발생: {str(e)}"

        return target

    async def close(self):
        if self.session:
            await self.session.close()

# main.py에서 호출하는 함수
async def charge(pin_string, cookie):
    cl = Cultureland()
    try:
        await cl.login(cookie)
        target_pin = Pin(pin_string)
        result = await cl.charge_process([target_pin])
        
        return {
            "status": "success" if result.amount > 0 else "error",
            "amount": result.amount,
            "message": result.message
        }
    finally:
        await cl.close()
