        # 1단계 클릭 후
        time.sleep(3)
        save(DONE_DIR, "modal")

        # 2단계: CSS 클래스로 직접 클릭 (1단계랑 동일 방식)
        confirm_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "button.btn-primary-md"
            ))
        )
        driver.execute_script("arguments[0].click();", confirm_btn)
        print(f"[{order_id}] 2단계 클릭 성공: '{confirm_btn.text}'")
        time.sleep(5)
