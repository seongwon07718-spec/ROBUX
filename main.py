from fastapi import FastAPI, Request, HTTPException
from fastapi.security import HTTPBearer

@app.post("/charge")
async def receive_charge(request: Request, data: ChargeData):

    # 시크릿 키 확인
    auth = request.headers.get("X-Secret-Key")
    if auth != CHARGE_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)

    if amount_match and name_match:
        key = f"{name_match.group(1)}_{amount_match.group(1).replace(',', '')}"
        pending_deposits[key] = True
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            pending_deposits[f"{fallback.group(1)}_{fallback.group(2)}"] = True

    return {"ok": True}
