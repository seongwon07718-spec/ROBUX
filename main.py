import aiohttp

class Pin:
    def init(self, pin_string):
        self.pin = pin_string.replace("-", "").strip()
        self.amount = 0
        self.message = "미처리"

class Cultureland:
    def init(self):
        self.session = None
        self.base_url = "https://m.cultureland.co.kr/"

    async def login(self, cookie):
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            "Cookie": cookie,
            "Accept": "application/json, text/plain, /",
            "Referer": f"{self.base_url}/cp/charge/touch.do",
            "Origin": self.base_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def charge_process(self, pins):
        if not self.session:
            return pins[0] if pins else None

        url = f"{self.base_url}/api/charge/touchConfirm"
        target = pins[0]
        p = target.pin

        payload = {
            "pin1": p[0:4], 
            "pin2": p[4:8], 
            "pin3": p[8:12], 
            "pin4": p[12:], 
            "is_scms": "N", 
            "scrId": "MT0101"
        }

        try:
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    target.message = f"서버 오류 (HTTP {resp.status})"
                    return target

                data = await resp.json()
                if str(data.get("result")) == "0":
                    target.amount = int(data.get("chargeAmount", 0))
                    target.message = "성공"
                else:
                    target.amount = 0
                    target.message = data.get("resultMsg", "핀번호 오류")
        except Exception as e:
            target.message = f"에러: {str(e)}"

        return target

    async def close(self):
        if self.session:
            await self.session.close()

async def charge(pin_string, cookie):
    cl = Cultureland()
    await cl.login(cookie)

    target_pin = Pin(pin_string)
    result = await cl.charge_process([target_pin])

    await cl.close()
    return result
