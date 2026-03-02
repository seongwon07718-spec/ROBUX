import aiohttp
import asyncio

class Pin:
    # 1. init -> __init__ 으로 수정
    def __init__(self, pin_string):
        self.pin = pin_string.replace("-", "").strip()
        self.amount = 0
        self.message = "미처리"

class Cultureland:
    # 2. init -> __init__ 으로 수정 (이 부분이 base_url 오류의 핵심 원인)
    def __init__(self):
        self.session = None
        self.base_url = "https://m.cultureland.co.kr"

    async def login(self, cookie):
        # 헤더 설정 시 base_url 참조 오류 해결됨
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/cp/charge/touch.do",
            "Origin": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def charge_process(self, pins):
        if not self.session:
            return pins[0] if pins else None

        # 3. API URL 경로 확인 (슬래시 중복 방지)
        url = f"{self.base_url}/api/charge/touchConfirm"
        target = pins[0]
        p = target.pin

        # 4. 핀번호 슬라이싱 안전장치 (16~19자리 대응)
        payload = {
            "pin1": p[0:4], 
            "pin2": p[4:8], 
            "pin3": p[8:12], 
            "pin4": p[12:], 
            "is_scms": "N", 
            "scrId": "MT0101"
        }

        try:
            # 5. response context manager 사용
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    target.amount = 0
                    target.message = f"서버 오류 (HTTP {resp.status})"
                    return target

                data = await resp.json()
                # 6. 컬쳐랜드 결과 값 처리 (문자열/숫자 혼용 대응)
                result_code = str(data.get("result", ""))
                if result_code == "0" or result_code == "0000":
                    target.amount = int(data.get("chargeAmount", 0))
                    target.message = "성공"
                else:
                    target.amount = 0
                    target.message = data.get("resultMsg", "핀번호 오류")
        except Exception as e:
            target.amount = 0
            target.message = f"네트워크 에러: {str(e)}"

        return target

    async def close(self):
        if self.session:
            await self.session.close()

# 7. main.py에서 호출할 때 반환 형식을 dict로 맞춰주기 위해 래핑
async def charge(pin_string, cookie):
    cl = Cultureland()
    try:
        await cl.login(cookie)
        target_pin = Pin(pin_string)
        result = await cl.charge_process([target_pin])
        
        # main.py의 res["status"] 등 조건문에 맞게 딕셔너리로 반환
        return {
            "status": "success" if result.amount > 0 else "error",
            "amount": result.amount,
            "message": result.message
        }
    finally:
        await cl.close()
