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
FAIL_DIR = "FAIL"

def buy_gamepass_selenium(pass_id: int, cookie: str) -> dict:
    os.makedirs(DONE_DIR, exist_ok=True)
    os.makedirs(FAIL_DIR, exist_ok=True)

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

    def save_screenshot(folder, label):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{label}_pass{pass_id}_{timestamp}.png")
        try:
            driver.save_screenshot(path)
            print(f"[스크린샷] 저장: {path}")
        except:
            pass
        return path

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

        # 1단계: 구매 버튼
        buy_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(@class,'PurchaseButton') or contains(text(),'구매')]"
            ))
        )
        buy_btn.click()
        print("[Selenium] 1단계 구매 버튼 클릭!")
        time.sleep(3)

        save_screenshot(DONE_DIR, "modal")

        # 2단계: JS로 모든 버튼 강제 클릭 시도
        result = driver.execute_script("""
            const btns = Array.from(document.querySelectorAll('button'));
            const visible = btns.filter(b => b.offsetParent !== null);
            const keywords = ['지금 구매하기', '지금 구매', 'Buy Now', 'buy now', 'Purchase'];
            for (const kw of keywords) {
                for (const btn of visible) {
                    if (btn.textContent.trim().includes(kw)) {
                        btn.click();
                        return '클릭성공: ' + btn.textContent.trim();
                    }
                }
            }
            // 못 찾으면 모든 버튼 텍스트 반환
            return '못찾음: ' + visible.map(b => b.textContent.trim()).join(' | ');
        """)
        print(f"[Selenium] JS 결과: {result}")

        if "못찾음" in result:
            # 버튼 클래스로 직접 찾기 (이전 로그에서 확인된 클래스)
            try:
                btn = driver.find_element(By.CSS_SELECTOR, 
                    "button.btn-primary-md, button[class*='confirm'], button[class*='purchase-btn']"
                )
                driver.execute_script("arguments[0].click();", btn)
                print(f"[Selenium] CSS로 클릭: {btn.text}")
            except Exception as e2:
                save_screenshot(FAIL_DIR, "fail_nobtn")
                return {"purchased": False, "reason": f"버튼 못 찾음: {result}"}

        time.sleep(4)
        save_screenshot(DONE_DIR, "success")

        page = driver.page_source
        if "already own" in page.lower() or "이미 소유" in page.lower():
            save_screenshot(FAIL_DIR, "already_own")
            return {"purchased": False, "reason": "이미 소유 중"}

        print(f"[Selenium] 구매 완료!")
        return {"purchased": True}

    except Exception as e:
        save_screenshot(FAIL_DIR, "error")
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
        return {"success": False, "message": "관리자 쿠키 없음", "order_id": None}

    result = buy_gamepass_selenium(pass_id, row[0])

    if not result.get("purchased"):
        return {"success": False, "message": result.get("reason", "구매 실패"), "order_id": None}

    order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
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
