from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import sqlite3
import random
import string
import os
from PIL import Image
import io
import requests
import threading
import queue

DATABASE = "robux_shop.db"
DONE_DIR = "DONE"
FAIL_DIR = "FAIL"

db_lock = threading.Lock()

# ─────────────────────────────────────────
# 대기열
# ─────────────────────────────────────────

purchase_queue = queue.Queue()
queue_status = {}


def queue_worker():
    while True:
        try:
            task = purchase_queue.get(timeout=1)
            if task is None:
                break

            order_id = task["order_id"]
            queue_status[order_id]["status"] = "processing"

            for oid, info in list(queue_status.items()):
                if info["status"] == "waiting":
                    info["position"] = max(1, info["position"] - 1)

            result = buy_gamepass_selenium(
                task["pass_id"],
                task["cookie"],
                order_id,
                task["user_id"]
            )
            queue_status[order_id]["result"] = result
            queue_status[order_id]["status"] = "done"
            purchase_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[워커 오류] {e}")


worker_thread = threading.Thread(target=queue_worker, daemon=True)
worker_thread.start()

# ─────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────

def get_current_robux(cookie: str) -> int:
    try:
        clean = cookie.strip()
        if "=" in clean:
            clean = clean.split("=", 1)[-1]
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", clean, domain=".roblox.com")
        me = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5).json()
        my_id = me.get("id")
        if not my_id:
            return 0
        eco = session.get(f"https://economy.roblox.com/v1/users/{my_id}/currency", timeout=5).json()
        return eco.get("robux", 0)
    except Exception:
        return 0


# ─────────────────────────────────────────
# 구매 함수
# ─────────────────────────────────────────

def buy_gamepass_selenium(pass_id: int, cookie: str, order_id: str, user_id: str = "") -> dict:
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
        path = os.path.join(folder, f"{label}_{user_id}_{order_id}_{ts}.png")
        try:
            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))
            crop_box = (0, 80, img.width, min(500, img.height))
            cropped = img.crop(crop_box)
            cropped.save(path)
        except Exception:
            driver.save_screenshot(path)
        return path

    def close_annoying_popups():
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
                    ) { btn.click(); }
                }
            """)
            time.sleep(1)
        except Exception:
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

        # 소유 여부 사전 확인
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", clean_cookie, domain=".roblox.com")
        me = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5).json()
        my_id = me.get("id")

        if not my_id:
            return {"purchased": False, "reason": "쿠키 인증 실패"}

        own_resp = session.get(
            f"https://inventory.roblox.com/v1/users/{my_id}/items/GamePass/{pass_id}",
            timeout=5
        ).json()
        if own_resp.get("data"):
            return {"purchased": False, "reason": "이미 소유 중인 게임패스"}

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
        except Exception:
            buy_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(@class,'PurchaseButton') or contains(text(),'구매')]"
                ))
            )

        driver.execute_script("arguments[0].click();", buy_btn)
        print(f"[{order_id}] 1단계 구매 버튼 클릭")
        time.sleep(3)

        # 2단계: 지금 구매하기
        clicked = False

        if not clicked:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='지금 구매하기']"))
                )
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                print(f"[{order_id}] 방법1 성공")
            except Exception:
                pass

        if not clicked:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[contains(text(),'지금 구매') or contains(text(),'Buy Now')]"
                    ))
                )
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                print(f"[{order_id}] 방법2 성공")
            except Exception:
                pass

        if not clicked:
            try:
                btn = driver.find_element(By.XPATH,
                    "//*[contains(text(),'지금 구매하기') or contains(text(),'Buy Now')]"
                )
                ActionChains(driver).move_to_element(btn).pause(0.5).click().perform()
                clicked = True
                print(f"[{order_id}] 방법3 성공")
            except Exception:
                pass

        if not clicked:
            result = driver.execute_script("""
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.offsetParent === null) continue;
                    const txt = btn.innerText.trim();
                    if (txt === '취소' || txt === 'Cancel' || txt === '×') continue;
                    const rect = btn.getBoundingClientRect();
                    if (rect.top > 540 && rect.top < 640 && rect.left > 250 && rect.left < 460) {
                        btn.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                        btn.dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
                        btn.dispatchEvent(new MouseEvent('click', {bubbles:true}));
                        return '성공:' + txt;
                    }
                }
                return '실패';
            """)
            if "성공" in result:
                clicked = True
                print(f"[{order_id}] 방법4 성공: {result}")

        if not clicked:
            result = driver.execute_script("""
                const modal = document.querySelector('[role="dialog"]') ||
                             document.querySelector('[class*="modal"]') ||
                             document.querySelector('[class*="purchase"]');
                if (!modal) return '모달없음';
                const btns = modal.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.offsetParent === null) continue;
                    const txt = btn.innerText.trim();
                    if (txt === '취소' || txt === 'Cancel' || txt === '×') continue;
                    btn.click();
                    return '성공:' + txt;
                }
                return '실패';
            """)
            if "성공" in result:
                clicked = True
                print(f"[{order_id}] 방법5 성공: {result}")

        if not clicked:
            save(FAIL_DIR, "btn_not_found")
            return {"purchased": False, "reason": "지금 구매하기 버튼 못 찾음"}

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
        print(f"[{order_id}] ❌ 실패: {e}")
        return {"purchased": False, "reason": str(e)}
    finally:
        driver.quit()


# ─────────────────────────────────────────
# 프로세스
# ─────────────────────────────────────────

def process_manual_buy_selenium(pass_id: int, user_id: str, money: int) -> dict:

    with db_lock:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()

            cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "관리자 쿠키 없음", "order_id": None, "screenshot": None}

            cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
            m = cur.fetchone()
            if m and m[0] == "1":
                return {"success": False, "message": "점검 중입니다", "order_id": None, "screenshot": None}

            cur.execute("SELECT value FROM config WHERE key = ?", (f"blacklist_{user_id}",))
            bl = cur.fetchone()
            if bl and bl[0] == "1":
                return {"success": False, "message": "구매가 제한된 유저입니다", "order_id": None, "screenshot": None}

            cur.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
                (money, user_id, money)
            )
            if cur.rowcount == 0:
                return {"success": False, "message": "잔액 부족", "order_id": None, "screenshot": None}

            # 로벅스 재고 확인
            current_robux = get_current_robux(row[0])
            pass_price = money

            try:
                clean = row[0].strip()
                if "=" in clean:
                    clean = clean.split("=", 1)[-1]
                session = requests.Session()
                session.cookies.set(".ROBLOSECURITY", clean, domain=".roblox.com")
                pass_info = session.get(
                    f"https://apis.roblox.com/game-passes/v1/game-passes/{pass_id}/details",
                    timeout=5
                ).json()
                price_info = pass_info.get("priceInformation") or {}
                pass_price = int(price_info.get("price") or price_info.get("defaultPriceInRobux") or money)

                if current_robux < pass_price:
                    return {
                        "success": False,
                        "message": f"로벅스 재고 부족 (필요: {pass_price:,} R$ / 현재: {current_robux:,} R$)",
                        "order_id": None,
                        "screenshot": None
                    }
            except Exception:
                pass

            # 잔액 선차감 + 주문 생성
            order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
            cur.execute(
                "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'pending')",
                (order_id, user_id, money, pass_price)
            )
            conn.commit()

    # 대기열 등록
    position = purchase_queue.qsize() + 1
    queue_status[order_id] = {
        "position": position,
        "status": "waiting",
        "result": None
    }
    purchase_queue.put({
        "pass_id": pass_id,
        "cookie": row[0],
        "order_id": order_id,
        "user_id": user_id
    })

    print(f"[{order_id}] 대기열 {position}번째 등록")

    # 완료될 때까지 대기
    while True:
        time.sleep(1)
        status = queue_status.get(order_id, {})
        if status.get("status") == "done":
            break

    result = queue_status[order_id]["result"]
    del queue_status[order_id]

    with db_lock:
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            if result.get("purchased"):
                cur.execute("UPDATE orders SET status = 'completed' WHERE order_id = ?", (order_id,))
                conn.commit()
                return {
                    "success": True,
                    "message": "✅ 구매 완료!",
                    "order_id": order_id,
                    "screenshot": result.get("screenshot")
                }
            else:
                cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (money, user_id))
                cur.execute("UPDATE orders SET status = 'failed' WHERE order_id = ?", (order_id,))
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
