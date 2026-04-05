        # 구매 버튼 클릭 후 대기
        buy_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(@class,'PurchaseButton') or contains(text(),'Buy') or contains(text(),'구매')]"
            ))
        )
        buy_btn.click()
        time.sleep(3)

        # 모달창 뜬 후 모든 버튼 출력해서 확인
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            print(f"버튼: '{btn.text}' / class: '{btn.get_attribute('class')}'")

        # 확인 버튼 - 여러 경우 시도
        confirm_selectors = [
            "//button[contains(text(),'Buy Now')]",
            "//button[contains(text(),'지금 구매')]",
            "//button[contains(text(),'Purchase')]",
            "//button[contains(text(),'확인')]",
            "//button[contains(@class,'confirm')]",
            "//button[contains(@class,'btn-primary')]",
            "//button[contains(@class,'modal')]",
        ]

        for selector in confirm_selectors:
            try:
                confirm_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"확인 버튼 찾음: {confirm_btn.text}")
                confirm_btn.click()
                print("클릭 성공!")
                break
            except:
                continue
