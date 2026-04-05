from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import sqlite3
import random
import string
import os

DATABASE = "robux_shop.db"
DONE_DIR = "DONE"

def buy_gamepass_selenium(pass_id: int, cookie: str) -> dict:
    os.makedirs(DONE_DIR, exist_ok=True)

    options = Options()
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
        time.sleep(4)

        # 1단계: 구매 버튼 클릭
        buy_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(@class,'PurchaseButton') or contains(text(),'구매')]"
            ))
        )
        buy_btn.click()
        print("[Selenium] 1단계 구매 버튼 클릭 완료")
        time.sleep(3)

        # 2단계: 지금 구매하기 클릭
        clicked = driver.execute_script("""
            const allBtns = document.querySelectorAll('button');
            for (const btn of allBtns) {
                if (!btn.offsetParent) continue;
                const txt = btn.textContent.trim();
                if (txt === '지금 구매하기' || txt.includes('지금 구매') || 
                    txt === 'Buy Now' || txt.includes('Buy Now')) {
                    btn.click();
                    return txt;
                }
            }
            return null;
        """)

        if clicked:
            print(f"[Selenium] 지금 구매하기 클릭 성공: '{clicked}'")
        else:
            confirm_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[text()='지금 구매하기' or contains(text(),'지금 구매') or text()='Buy Now']"
                ))
            )
            confirm_btn.click()
            print("[Selenium] XPATH로 클릭 성공!")

        time.sleep(4)

        # 구매 완료 스크린샷 저장
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(DONE_DIR, f"pass_{pass_id}_{timestamp}.png")
        driver.save_screenshot(screenshot_path)
        print(f"[Selenium] 구매 완료 스크린샷 저장: {screenshot_path}")

        page = driver.page_source
        if "already own" in page.lower() or "이미 소유" in page.lower():
            return {"purchased": False, "reason": "이미 소유 중인 게임패스"}

        print(f"[Selenium] 구매 완료! pass_id={pass_id}")
        return {"purchased": True, "screenshot": screenshot_path}

    except Exception as e:
        # 실패 스크린샷도 저장
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            fail_path = os.path.join(DONE_DIR, f"FAIL_pass_{pass_id}_{timestamp}.png")
            driver.save_screenshot(fail_path)
            print(f"[Selenium] 실패 스크린샷 저장: {fail_path}")
        except:
            pass
        print(f"[Selenium] 오류: {e}")
        return {"purchased": False, "reason": str(e)}
    finally:
        driver.quit()


def process_manual_buy_selenium(pass_id: int, user_id: str, money: int) -> dict:
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    if not row:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다.", "order_id": None}

    result = buy_gamepass_selenium(pass_id, row[0])

    if not result.get("purchased"):
        reason = result.get("reason", "구매 실패")
        return {"success": False, "message": reason, "order_id": None}

    order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (money, user_id)
        )
        cur.execute(
            "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'completed')",
            (order_id, user_id, money, money)
        )
        conn.commit()

    return {"success": True, "message": "구매 완료!", "order_id": order_id}


if __name__ == "__main__":
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    result = buy_gamepass_selenium(1784490889, row[0])
    print(f"결과: {result}")
