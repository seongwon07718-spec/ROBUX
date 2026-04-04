    # 모달 내부 on_submit 예시
    pass_id = extract_pass_id(raw_val) # 알렉스님이 보내준 사진의 그 함수
    
    # [수정된 가격 추출 방식]
    gamepass_price = fetch_gamepass_price(pass_id, admin_cookie)
    
    if gamepass_price == 0:
        # 가격이 0원(무료)이거나 정보를 못 불러온 경우 처리
        # (필요하다면 여기서 "정보를 불러올 수 없습니다" 메시지 출력)
        pass

    # 비율(rate)에 따른 원화 계산
    money = int((gamepass_price / rate) * 10000) 
