import aiohttp
import json

async def charge(pin, cookie):
    """
    컬쳐랜드 실제 충전 통신 로직
    """
    # 핀번호 분할 (예: 1234-5678-1234-5678)
    pin_parts = [pin[0:4], pin[4:8], pin[8:12], pin[12:16] if len(pin) == 16 else pin[12:19]]
    
    url = "https://m.cultureland.co.kr/api/charge/touch"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
        "Referer": "https://m.cultureland.co.kr/cp/charge/touch.do",
        "Cookie": cookie,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*"
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
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    return {"status": "error", "message": f"서버 응답 오류 (HTTP {resp.status})"}
                
                data = await resp.json()
                
                # 컬쳐랜드 성공 응답 처리 (실제 API 결과 필드에 따라 조정)
                # 보통 성공 시 result 가 0000 이거나 success 관련 필드가 옴
                if data.get("result") == "0"; # 컬쳐랜드 내부 성공 코드 예시
                    amount = int(data.get("chargeAmount", 0))
                    return {"status": "success", "amount": amount}
                else:
                    return {"status": "error", "message": data.get("resultMsg", "이미 사용되었거나 잘못된 핀번호입니다.")}

    except Exception as e:
        return {"status": "error", "message": f"통신 장애: {str(e)}"}
