    def save(folder, label):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{label}_{user_id}_{order_id}_{ts}.png")
        try:
            # 1단계: 전체 화면 캡처 (image_2.png처럼 캡처됨)
            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))
            
            # 2단계: [수정 핵심] 불필요한 부분을 잘라냅니다.
            # (왼쪽, 위, 오른쪽, 아래)
            # 왼쪽 메뉴바 영역(약 250px)과 상단 헤더 영역(약 60px)을 제거합니다.
            # (250, 60, 1000, 850) -> 왼쪽 250px 제거, 위쪽 60px 제거
            crop_box = (250, 60, min(1000, img.width), min(850, img.height)) 
            cropped = img.crop(crop_box)
            cropped.save(path)
            
            print(f"[{order_id}] 크롭된 스크린샷 저장 완료: {path}")
        except Exception as e:
            print(f"이미지 저장/크롭 중 오류: {e}")
            # 크롭 실패 시 일단 전체 화면이라도 저장 (보험)
            driver.save_screenshot(path)
        return path
