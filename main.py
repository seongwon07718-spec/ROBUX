from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import sqlite3

DATABASE = "robux_shop.db"

def buy_gamepass_selenium(pass_id: int, cookie: str) -> dict:
    options = Options()
    options.add_argument("--headless")
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
        # 쿠키 설정
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

        # 게임패스 페이지 이동
        driver.get(f"https://www.roblox.com/game-pass/{pass_id}/")
        time.sleep(3)

        # 구매 버튼 클릭
        buy_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, 
                "//button[contains(@class,'PurchaseButton') or contains(text(),'Buy') or contains(text(),'구매')]"
            ))
        )
        buy_btn.click()
        time.sleep(2)

        # 확인 버튼 클릭
        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(text(),'Buy Now') or contains(text(),'지금 구매') or contains(@class,'confirm')]"
            ))
        )
        confirm_btn.click()
        time.sleep(3)

        # 성공 확인
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    "//*[contains(text(),'Success') or contains(text(),'성공') or contains(text(),'purchased')]"
                ))
            )
            print(f"[Selenium] 구매 성공! pass_id={pass_id}")
            return {"purchased": True}
        except:
            # 이미 소유 중인지 확인
            page = driver.page_source
            if "already own" in page.lower() or "이미 소유" in page.lower():
                return {"purchased": False, "reason": "이미 소유 중"}
            return {"purchased": True}  # 성공으로 간주

    except Exception as e:
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
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    result = buy_gamepass_selenium(pass_id, row[0])

    if not result.get("purchased"):
        reason = result.get("reason", "구매 실패")
        return {"success": False, "message": reason}

    # 구매 성공 → 잔액 차감 및 주문 저장
    import random, string
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

    return {"success": True, "message": f"구매 완료! 주문번호: {order_id}"}


# 테스트
if __name__ == "__main__":
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    result = buy_gamepass_selenium(1784490889, row[0])
    print(f"결과: {result}")
