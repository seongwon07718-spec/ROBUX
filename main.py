    def save(folder, label):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{label}_{user_id}_{order_id}_{ts}.png")
        try:
            # 전체 스크린샷 찍고 게임패스 영역만 크롭
            from PIL import Image
            import io

            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))

            # 브라우저 창 크기
            w = driver.execute_script("return window.innerWidth")
            h = driver.execute_script("return window.innerHeight")

            # 게임패스 정보 영역만 크롭 (상단 네비 제외, 하단 푸터 제외)
            # 대략 y: 80~500, x: 0~전체
            crop_box = (0, 80, img.width, min(500, img.height))
            cropped = img.crop(crop_box)
            cropped.save(path)

        except Exception:
            driver.save_screenshot(path)
        return path
