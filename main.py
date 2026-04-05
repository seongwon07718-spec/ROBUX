def buy_gamepass_selenium(pass_id: int, cookie: str) -> dict:
    options = Options()
    # --headless 제거!
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get("https://www.roblox.com")
        time.sleep(2)

        clean_cookie = cookie.strip()
        if "=" in clean_cookie:
            clean_cookie = clean_cookie.split("=", 1)[-1]

        driver.add_cookie({
            "name": ".ROBLOSECURITY",
            "value": clean_cookie,
            "domain": ".roblox.com",
            "path": "/",
        })

        driver.get(f"https://www.roblox.com/game-pass/{pass_id}/")
        time.sleep(3)

        print(f"[Selenium] 페이지 제목: {driver.title}")
        print(f"[Selenium] URL: {driver.current_url}")

        buy_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(@class,'PurchaseButton') or contains(text(),'Buy') or contains(text(),'구매')]"
            ))
        )
        buy_btn.click()
        time.sleep(2)

        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(text(),'Buy Now') or contains(text(),'지금 구매')]"
            ))
        )
        confirm_btn.click()
        time.sleep(3)

        print(f"[Selenium] 구매 완료!")
        return {"purchased": True}

    except Exception as e:
        print(f"[Selenium] 오류: {e}")
        return {"purchased": False, "reason": str(e)}
    finally:
        driver.quit()
