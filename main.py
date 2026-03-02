import aiohttp
import asyncio

class Pin:
    def __init__(self, pin_string):
        self.pin = pin_string.replace("-", "").strip()
        self.amount = 0
        self.message = "미처리"

class Cultureland:
    def __init__(self):
        self.session = None
        self.base_url = "https://m.cultureland.co.kr"

    async def login(self, cookie):
        # 1. 브라우저와 동일한 헤더 구성 (강화된 인식 로직)
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded", # 데이터 전송 방식 고정
            "Cookie": cookie,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/csh/cshGiftCardCfrm.do",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        # SSL 인증 무시 및 커넥션 풀 최적화
        connector = aiohttp.TCPConnector(ssl=False, force_close=True)
        self.session = aiohttp.ClientSession(headers=headers, connector=connector)

    async def charge_process(self, pins):
        if not self.session:
            return pins[0] if pins else None

        url = f"{self.base_url}/csh/cshGiftCardCfrm.do"
        target = pins[0]
        
        # 2. Payload를 JSON이 아닌 Form Data 형식으로 전송 (인식 강화)
        payload = {
            "txt_pin_no": target.pin,
            "is_scms": "N",
            "scrId": "MT0101"
        }

        try:
            # 3. 리다이렉트 방지(allow_redirects=False)로 세션 체크 강화
            async with self.session.post(url, data=payload, timeout=15, allow_redirects=False) as resp:
                # HTTP 302(리다이렉트)나 200인데 HTML이 오면 무조건 세션 만료
                content_type = resp.headers.get("Content-Type", "")
                
                if resp.status == 302 or "text/html" in content_type:
                    target.amount = 0
                    target.message = "❌ 세션 거부 (쿠키를 다시 복사하여 '로그인 유지' 체크 확인)"
                    return target

                if resp.status == 200:
                    data = await resp.json()
                    result_code = str(data.get("result", ""))
                    
                    if result_code == "0" or "성공" in data.get("resultMsg", ""):
                        target.amount = int(data.get("chargeAmount", 0))
                        target.message = "성공"
                    else:
                        target.amount = 0
                        target.message = data.get("resultMsg", "핀번호 오류")
                else:
                    target.message = f"서버 응답 오류 ({resp.status})"
                    
        except Exception as e:
            target.message = f"통신 강화 에러: {str(e)}"

        return target

    async def close(self):
        if self.session:
            await self.session.close()

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
