app = FastAPI()
pending_deposits = {}

class ChargeData(BaseModel):
    message: str
    server_id: str = ""
    pw: str = ""

@app.post("/charge")
async def receive_charge(request: Request, data: ChargeData):

    server_id = request.headers.get("server-id") or data.server_id if hasattr(data, 'server_id') else None
    pw = request.headers.get("pw") or data.pw if hasattr(data, 'pw') else None

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'charge_server_id'")
        saved_id = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'charge_pw'")
        saved_pw = cur.fetchone()

    if not saved_id or not saved_pw:
        raise HTTPException(status_code=500, detail="Server not configured")

    if server_id != saved_id[0] or pw != saved_pw[0]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)

    name = None
    amount = None

    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        pending_deposits[f"{name}_{amount}"] = True
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            name = fallback.group(1)
            amount = fallback.group(2)
            pending_deposits[f"{name}_{amount}"] = True

    return {
        "ok": True,
        "message": f"{name} / {int(amount):,}원 충전 신청 완료" if name and amount else "처리 완료"
    }

web_app = FastAPI()

@web_app.get("/")
async def root():
    return {"status": "ok"}

@web_app.get("/purchase-log")
async def purchase_log_page():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "purchase_log.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>오류: {e}</h1>")

@web_app.get("/api/purchase-logs")
async def get_purchase_logs(limit: int = 20, offset: int = 0):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name
            FROM orders WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT ? OFFSET ?
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
