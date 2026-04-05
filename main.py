def buy_gamepass_selenium(pass_id: int, cookie: str, order_id: str, user_id: str = "") -> dict:
    # ...
    def save(folder, label):
        ts = time.strftime("%Y%m%d_%H%M%S")
        # success_유저ID_주문번호 형식
        path = os.path.join(folder, f"{label}_{user_id}_{order_id}_{ts}.png")
        try:
            driver.save_screenshot(path)
        except:
            pass
        return path
