import aiohttp

async def charge(pin, cookie):
    # 핀번호 분할 로직 (16~19자리 대응)
    pin_parts = [pin[0:4], pin[4:8], pin[8:12], pin[12:16] if len(pin) == 16 else pin[12:19]]
    
    # 404를 방지하기 위한 실제 API 엔드포인트
    url = "https://m.cultureland.co.kr/api/charge/touch" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://m.cultureland.co.kr",
        "Referer": "https://m.cultureland.co.kr/cp/charge/touch.do", # 이게 빠지면 404가 뜹니다
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    payload = {
        "pin1": pin_parts[0],
        "pin2": pin_parts[1],
        "pin3": pin_parts[2],
        "pin4": pin_parts[3],
        "is_scms": "N"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 타임아웃 10초 설정하여 무한 대기 방지
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 404:
                    return {"status": "error", "message": "서버 경로를 찾을 수 없음 (404). 주소 확인 필요."}
                
                if resp.status != 200:
                    return {"status": "error", "message": f"서버 응답 오류 (HTTP {resp.status})"}
                
                data = await resp.json()
                
                # 컬쳐랜드 성공 코드 (0 또는 0000 등 실제 응답에 맞춰 확인 필요)
                if str(data.get("result")) in ["0", "0000"]:
                    amount = int(data.get("chargeAmount", 0))
                    return {"status": "success", "amount": amount}
                else:
                    return {"status": "error", "message": data.get("resultMsg", "이미 사용되었거나 잘못된 핀번호입니다.")}

    except Exception as e:
        return {"status": "error", "message": f"통신 장애: {str(e)}"}
