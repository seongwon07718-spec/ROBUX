import aiohttp
import json

async def charge(pin, cookie):
    # 핀번호 분할 (16~19자리 대응)
    pin_parts = [pin[0:4], pin[4:8], pin[8:12], pin[12:len(pin)]]
    
    # [중요] 404 방지를 위한 실제 모바일 충전 처리 주소
    url = "https://m.cultureland.co.kr/api/charge/touchConfirm" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://m.cultureland.co.kr",
        "Referer": "https://m.cultureland.co.kr/cp/charge/touch.do",
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 컬쳐랜드 서버가 요구하는 데이터 형식
    payload = {
        "pin1": pin_parts[0],
        "pin2": pin_parts[1],
        "pin3": pin_parts[2],
        "pin4": pin_parts[3],
        "is_scms": "N",
        "scrId": "MT0101" # 실제 요청에 포함되는 스크린 ID
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                # 404가 뜨면 주소나 세션이 완전히 막힌 것임
                if resp.status == 404:
                    return {"status": "error", "message": "컬쳐랜드 주소 응답 없음(404). 세션 만료 가능성."}
                
                data = await resp.json()
                
                # 결과값이 0이면 성공, 그 외는 실패 메시지 출력
                if str(data.get("result")) == "0":
                    amount = int(data.get("chargeAmount", 0))
                    return {"status": "success", "amount": amount}
                else:
                    msg = data.get("resultMsg", "핀번호 오류 또는 이미 사용됨")
                    return {"status": "error", "message": msg}

    except Exception as e:
        return {"status": "error", "message": f"서버 연결 실패: {str(e)}"}
