@app.get("/api/purchase-logs")
async def get_purchase_logs(limit: int = 20, offset: int = 0):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name
            FROM orders
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed' AND DATE(created_at) = DATE('now')")
        today = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed'")
        total_amount = cur.fetchone()[0]

    logs = []
    for row in rows:
        order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name = row
        logs.append({
            "order_id": order_id,
            "roblox_name": roblox_name or "유저",
            "roblox_id": roblox_id or "",
            "amount": amount,
            "robux": robux,
            "gamepass_name": gamepass_name or "게임패스",
            "created_at": created_at,
            "avatar_url": f"https://www.roblox.com/headshot-thumbnail/image?userId={roblox_id}&width=150&height=150&format=png" if roblox_id else ""
        })

    return {"logs": logs, "stats": {"total": total, "today": today, "total_amount": total_amount}}
