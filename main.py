@app.post("/charge")
async def receive_charge(request: Request, data: ChargeData):

    # server_id, pw 인증
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
