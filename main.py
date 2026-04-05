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

DATABASE = "robux_shop.db"
DONE_DIR = "DONE"
FAIL_DIR = "FAIL"

db_lock = threading.Lock()


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
        except:
            pass
        return path

    def close_annoying_popups():
        """구매 완료 후 뜨는 안내 팝업 자동 X 닫기 - 구매 버튼은 절대 안 건드림"""
        try:
            driver.execute_script("""
                const safeSkip = ['지금 구매하기', 'buy now', '구매', '취소', 'cancel'];
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.offsetParent === null) continue;
                    const txt = btn.innerText.trim().toLowerCase();
                    const cls = (btn.className || '').toLowerCase();
                    const html = btn.innerHTML;
                    if (safeSkip.some(k => txt.includes(k))) continue;
                    if (
                        txt === '확인' || txt === 'ok' ||
                        txt === '닫기' || txt === 'close' ||
                        html.includes('×') || html.includes('✕') || html.includes('✖') ||
                        cls.includes('close') || cls.includes('dismiss')
                    ) {
                        btn.click();
                    }
                }
            """)
            time.sleep(1)
        except:
            pass

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
        print(f"[{order_id}] 1단계 구매 버튼 클릭")
        time.sleep(3)
        save(DONE_DIR, "modal")

        # 2단계: 지금 구매하기 버튼 좌표로 직접 클릭
        result = driver.execute_script("""
            const btns = document.querySelectorAll('button');
            
            // 1순위: 텍스트 정확히 매칭
            for (const btn of btns) {
                if (btn.offsetParent === null) continue;
                const txt = btn.innerText.trim();
                if (txt === '지금 구매하기' || txt === 'Buy Now') {
                    const rect = btn.getBoundingClientRect();
                    btn.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    btn.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    return '텍스트매칭: ' + txt;
                }
            }
            
            // 2순위: 모달 내 좌표로 찾기 (지금구매하기는 모달 하단 왼쪽)
            for (const btn of btns) {
                if (btn.offsetParent === null) continue;
                const rect = btn.getBoundingClientRect();
                const txt = btn.innerText.trim();
                if (txt === '취소' || txt === 'Cancel' || txt === '×') continue;
                if (rect.top > 540 && rect.top < 630 &&
                    rect.left > 250 && rect.left < 460 &&
                    rect.width > 80) {
                    btn.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    btn.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    return '좌표클릭: ' + txt + ' top=' + Math.round(rect.top);
                }
            }
            
            return '실패';
        """)
        print(f"[{order_id}] 2단계: {result}")

        if "실패" in result:
            save(FAIL_DIR, "btn_not_found")
            return {"purchased": False, "reason": "지금 구매하기 버튼 못 찾음"}

        # 구매 완료 후 안내 팝업 자동 닫기
        for _ in range(3):
            time.sleep(2)
            close_annoying_popups()

        success_path = save(DONE_DIR, "success")

        page_after = driver.page_source
        if "already own" in page_after.lower() or "이미 소유" in page_after.lower():
            save(FAIL_DIR, "already_own")
            return {"purchased": False, "reason": "이미 소유 중"}

        print(f"[{order_id}] ✅ 구매 성공!")
        return {"purchased": True, "screenshot": success_path}

    except Exception as e:
        save(FAIL_DIR, "error")
        print(f"[{order_id}] ❌ 구매 실패: {e}")
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
                return {"success": False, "message": "관리자 쿠키 없음", "order_id": None, "screenshot": None}

            cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            if not user or user[0] < money:
                return {"success": False, "message": "잔액 부족", "order_id": None, "screenshot": None}

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

    result = buy_gamepass_selenium(pass_id, row[0], order_id)

    with db_lock:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            if result.get("purchased"):
                cur.execute(
                    "UPDATE orders SET status = 'completed' WHERE order_id = ?",
                    (order_id,)
                )
                conn.commit()
                return {
                    "success": True,
                    "message": "✅ 구매 완료!",
                    "order_id": order_id,
                    "screenshot": result.get("screenshot")
                }
            else:
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
                    "message": f"❌ {result.get('reason', '구매 실패')}",
                    "order_id": None,
                    "screenshot": None
                }


if __name__ == "__main__":
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    result = buy_gamepass_selenium(1784490889, row[0], "TEST001")
    print(f"결과: {result}")
