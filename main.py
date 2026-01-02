# --- [보안 강화된 정밀 OCR 함수] ---
def get_exact_nickname(region):
    """대소문자 구분을 위해 전처리를 극대화한 버전"""
    screenshot = pyautogui.screenshot(region=region)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # 노이즈 제거 및 선명도 향상
    img = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 이진화 (글자 테두리를 더욱 날카롭게)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # 3배 확대하여 대소문자 특징 부각
    resized = cv2.resize(thresh, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    
    # psm 7: 한 줄 텍스트 모드 / oem 3: 기본 엔진
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    text = pytesseract.image_to_string(resized, config=custom_config, lang='eng')
    
    return text.strip() # .lower()를 제거하여 대소문자 유지

# --- [안전 가동 루프] ---
async def start_secure_automation(interaction, seller_nick):
    # ... (상략) ...
    try:
        while True:
            # 다중 픽셀 검사 (창이 정확히 중앙에 떴는지 확인)
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=15):
                await asyncio.sleep(1) # 창이 완전히 뜰 때까지 대기
                
                detected_name = get_exact_nickname(NICK_REGION)
                print(f"🔍 [보안판독] 인식됨: {detected_name} | 목표: {seller_nick}")

                # 대소문자까지 완벽하게 일치해야 수락
                if detected_name == seller_nick:
                    print("✅ 닉네임 완벽 일치! 수락 진행")
                    force_click(ACCEPT_BTN)
                    break
                else:
                    print(f"⚠️ 경고: 닉네임 불일치 (사칭 의심). 감지된 이름: {detected_name}")
                    # 여기서 바로 거절하지 않고 관리자 로그를 남기는 것이 더 안전합니다.
            
            await asyncio.sleep(0.7)
