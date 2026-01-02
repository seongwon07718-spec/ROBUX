async with aiohttp.ClientSession() as session:
    url = f"https://users.roblox.com/v1/users/{roblox_id}"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                # 프로필 소개 추출 및 인증 코드 포함 여부 확인
                description = data.get("description", "")
                # 인증 코드 체크 로직
            else:
                # API 에러 상태 기록 및 처리
                print(f"Roblox API returned status {resp.status} for user {roblox_id}")
                # 필요 시 재시도 로직 구현
    except Exception as e:
        print(f"Roblox API 호출 중 오류 발생: {e}")
        # 예외 발생 시 처리 로직
