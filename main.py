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
import threading
from concurrent.futures import ThreadPoolExecutor

DATABASE = "robux_shop.db"
DONE_DIR = "DONE"
FAIL_DIR = "FAIL"

# DB 업데이트만 락 (구매는 동시 가능)
db_lock = threading.Lock()

# 최대 동시 구매 수
MAX_CONCURRENT = 5
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)

def buy_gamepass_selenium(pass_id: int, cookie: str, order_id: str) -> dict:
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

    def save(folder, label):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"{label}_order{order_id}_pass{pass_id}_{ts}.png")
        try:
            driver.save_screenshot(path)
            print(f"[스크린샷] {path}")
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

        page = driver.page_source
        if "already own" in page.lower() or "이미 소유" in page.lower():
            save(FAIL_DIR, "already_own")
            return {"purchased": False, "reason": "이미 소유 중인 게임패스"}

        # 1단계: 구매 버튼
        try:
            buy_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button.btn-fixed-width-lg.btn-primary-lg.PurchaseButton"
                ))
            )
        except:
            buy_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(@class,'PurchaseButton') or contains(text(),'구매')]"
                ))
            )

        driver.execute_script("arguments[0].click();", buy_btn)
        print(f"[{order_id}] 1단계 구매 버튼 클릭!")
        time.sleep(4)

        save(DONE_DIR, "modal")

        # 2단계: 지금 구매하기 버튼
        confirmed = False

        # 방법 1: CSS
        selectors = [
            "[role='dialog'] button.btn-primary-md",
            "[class*='modal'] button.btn-primary-md",
            "[class*='purchase'] button.btn-primary-md",
            "button.btn-primary-md",
        ]
        for sel in selectors:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                driver.execute_script("arguments[0].click();", btn)
                print(f"[{order_id}] CSS 클릭: '{btn.text}'")
                confirmed = True
                break
            except:
                continue

        # 방법 2: XPATH
        if not confirmed:
            for xp in [
                "//button[text()='지금 구매하기']",
                "//button[contains(text(),'지금 구매')]",
                "//button[text()='Buy Now']",
                "//button[contains(text(),'Buy Now')]",
            ]:
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"[{order_id}] XPATH 클릭: '{btn.text}'")
                    confirmed = True
                    break
                except:
                    continue

        # 방법 3: React fiber
        if not confirmed:
            result_js = driver.execute_script("""
                function clickReact(el) {
                    const keys = Object.keys(el);
                    const fiberKey = keys.find(k => 
                        k.startsWith('__reactFiber') || 
                        k.startsWith('__reactInternalInstance')
                    );
                    if (!fiberKey) return false;
                    let node = el[fiberKey];
                    while (node) {
                        if (node.memoizedProps && node.memoizedProps.onClick) {
                            node.memoizedProps.onClick({bubbles: true, cancelable: true});
                            return true;
                        }
                        node = node.return;
                    }
                    return false;
                }
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (!btn.offsetParent) continue;
                    const cls = btn.className || '';
                    if (cls.includes('primary') || cls.includes('confirm') || cls.includes('buy')) {
                        if (clickReact(btn)) return 'React: ' + btn.textContent.trim();
                        btn.click();
                        return 'DOM: ' + btn.textContent.trim();
                    }
                }
                return '실패';
            """)
            print(f"[{order_id}] React: {result_js}")
            if "실패" not in result_js:
                confirmed = True

        if not confirmed:
            save(FAIL_DIR, "btn_not_found")
            return {"purchased": False, "reason": "지금 구매하기 버튼 못 찾음"}

        time.sleep(5)

        # 성공 확인
        page_after = driver.page_source
        if "error" not in page_after.lower() and "실패" not in page_after.lower():
            save(DONE_DIR, "success")
            print(f"[{order_id}] ✅ 구매 성공!")
            return {"purchased": True}

        save(FAIL_DIR, "unknown")
        return {"purchased": False, "reason": "구매 결과 확인 불가"}

    except Exception as e:
        save(FAIL_DIR, "error")
        print(f"[{order_id}] ❌ 오류: {e}")
        return {"purchased": False, "reason": str(e)}
    finally:
        driver.quit()


def process_manual_buy_selenium(pass_id: int, user_id: str, money: int) -> dict:
    with db_lock:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "관리자 쿠키 없음", "order_id": None}

            cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            if not user or user[0] < money:
                return {"success": False, "message": "잔액 부족", "order_id": None}

            # 잔액 선차감 (동시 구매 중복 방지)
            order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (money, user_id)
            )
            cur.execute(
                "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'pending')",
                (order_id, user_id, money, money)
            )
            conn.commit()

    # 구매 실행 (락 없이 동시 실행 가능)
    result = buy_gamepass_selenium(pass_id, row[0], order_id)

    with db_lock:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            if result.get("purchased"):
                # 성공 → 상태 업데이트
                cur.execute(
                    "UPDATE orders SET status = 'completed' WHERE order_id = ?",
                    (order_id,)
                )
                conn.commit()
                return {"success": True, "message": "✅ 구매 완료!", "order_id": order_id}
            else:
                # 실패 → 잔액 복구 + 주문 실패 처리
                cur.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (money, user_id)
                )
                cur.execute(
                    "UPDATE orders SET status = 'failed' WHERE order_id = ?",
                    (order_id,)
                )
                conn.commit()
                return {
                    "success": False,
                    "message": f"❌ 구매 실패: {result.get('reason', '오류')}",
                    "order_id": None
                }


if __name__ == "__main__":
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    result = buy_gamepass_selenium(1784490889, row[0], "TEST001")
    print(f"결과: {result}")
