@web_app.get("/get_latest_order")
async def get_latest_order():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, target_id, pass_id
            FROM gift_queue
            WHERE status = 'processing'
            ORDER BY rowid ASC
            LIMIT 1
        """)
        row = cur.fetchone()
    if row:
        return {"order_id": row[0], "target_id": row[1], "pass_id": row[2]}
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="no orders")


@web_app.get("/complete_order")
async def complete_order(order_id: str, status: str):
    if status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="invalid status")
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE gift_queue SET status = ? WHERE order_id = ?",
            (status, order_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="order not found")
    return {"success": True}
