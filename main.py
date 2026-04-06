            # 잔액 음수 방지 - DB 레벨에서 차단
            cur.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
                (money, user_id, money)
            )
            if cur.rowcount == 0:
                return {"success": False, "message": "잔액 부족", "order_id": None, "screenshot": None}
