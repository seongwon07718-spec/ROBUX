    def save(folder, label):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{label}_{user_id}_{order_id}_{ts}.png")
        try:
            # 전체 화면 캡처
            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))
            
            # [수정 포인트] 
            # 첫 번째 사진처럼 정보를 다 담기 위해 하단 범위를 500에서 800 이상으로 늘립니다.
            # 보통 로블록스 아이템 페이지 상단 정보는 800px 정도면 충분히 담깁니다.
            crop_box = (0, 0, img.width, min(850, img.height)) 
            cropped = img.crop(crop_box)
            cropped.save(path)
        except Exception as e:
            print(f"이미지 저장 중 오류: {e}")
            driver.save_screenshot(path)
        return path
