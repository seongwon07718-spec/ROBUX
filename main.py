            cur.execute(
                "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'charge')",
                ("".join(random.choices(string.ascii_uppercase + string.digits, k=10)), user_id, 금액, 0)
            )
