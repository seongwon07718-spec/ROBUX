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

def close_popups(driver, order_id):
    """X버튼, 확인버튼 등 방해되는 팝업 모두 닫기"""
    try:
        result = driver.execute_script("""
            const closeKeywords = ['닫기', '확인', 'close', 'ok', '×', '✕'];
            const skipKeywords = ['지금 구매하기', 'buy now', '구매', '취소', 'cancel'];
            
            const btns = document.querySelectorAll('button, [role="button"]');
            let closed = [];
            
            for (const btn of btns) {
                if (btn.offsetParent === null) continue;
                const txt = btn.innerText.trim().toLowerCase();
                const cls = (btn.className || '').toLowerCase();
                
                // 구매 관련 버튼은 건드리지 않음
                if (skipKeywords.some(k => txt.includes(k))) continue;
                
                // X버튼 또는 확인버튼 닫기
                if (closeKeywords.some(k => txt.includes(k.toLowerCase())) || 
                    cls.includes('close') || cls.includes('dismiss') ||
                    btn.innerHTML.includes('×') || btn.innerHTML.includes('✕')) {
                    btn.click();
                    closed.push(txt || cls);
                }
            }
            return closed.length > 0 ? '팝업닫기: ' + closed.join(', ') : '팝업없음';
        """)
        print(f"[{order_id}] 팝업처리: {result}")
        time.sleep(1)
    except:
        pass


def verify_purchase_modal(driver, pass_id, order_id) -> bool:
    """구매 모달창에서 올바른 게임패스인지 확인"""
    try:
        modal_text = driver.execute_script("""
            const modal = document.querySelector('[role="dialog"]') ||
                         document.querySelector('[class*="modal"]');
            return modal ? modal.innerText : '';
        """)
        print(f"[{order_id}] 모달 텍스트: {modal_text[:200]}")
        
        # 모달이 열려있으면 OK
        if modal_text and len(modal_text) > 10:
            return True
        return False
    except:
        return False


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

        # 페이지 로드 후 방해 팝업 닫기
        close_popups(driver, order_id)

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
        time.sleep(3)

        # 모달 뜬 후 방해 팝업 먼저 닫기
        close_popups(driver, order_id)
        time.sleep(1)

        save(DONE_DIR, "modal")

        # 구매 모달 확인
        if not verify_purchase_modal(driver, pass_id, order_id):
            save(FAIL_DIR, "modal_not_found")
            return {"purchased": False, "reason": "구매 모달창을 찾을 수 없음"}

        # 2단계: "지금 구매하기" 텍스트 정확히 매칭해서 클릭
        result = driver.execute_script("""
            const btns = document.querySelectorAll('button');
            const targets = ['지금 구매하기', 'Buy Now', '지금구매하기'];
            
            for (const btn of btns) {
                if (btn.offsetParent === null) continue;
                const txt = btn.innerText.trim();
                if (targets.includes(txt)) {
                    btn.click();
                    return '성공: ' + txt;
                }
            }
            
            // 못 찾으면 모달 안에서 primary 버튼 찾기
            const modal = document.querySelector('[role="dialog"]') ||
                         document.querySelector('[class*="modal"]');
            if (modal) {
                const modalBtns = modal.querySelectorAll('button');
                for (const btn of modalBtns) {
                    if (btn.offsetParent === null) continue;
                    const txt = btn.innerText.trim();
                    const cls = btn.className || '';
                    // 취소/X 버튼 제외
                    if (txt === '취소' || txt === 'Cancel' || txt === '×') continue;
                    if (cls.includes('primary') || cls.includes('confirm')) {
                        btn.click();
                        return '모달primary클릭: ' + txt;
                    }
                }
            }
            
            return '실패: 버튼없음';
        """)
        print(f"[{order_id}] 2단계 결과: {result}")

        if "실패" in result:
            save(FAIL_DIR, "btn_not_found")
            return {"purchased": False, "reason": f"지금 구매하기 버튼 못 찾음"}

        time.sleep(5)

        # 구매 후 팝업 있으면 닫기
        close_popups(driver, order_id)
        time.sleep(2)

        save(DONE_DIR, "success")

        page_after = driver.page_source
        if "already own" in page_after.lower() or "이미 소유" in page_after.lower():
            save(FAIL_DIR, "already_own")
            return {"purchased": False, "reason": "이미 소유 중"}

        print(f"[{order_id}] ✅ 구매 성공!")
        return {"purchased": True}

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
                return {"success": True, "message": "✅ 구매 완료!", "order_id": order_id}
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
                    "order_id": None
                }


if __name__ == "__main__":
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    result = buy_gamepass_selenium(1784490889, row[0], "TEST001")
    print(f"결과: {result}")
