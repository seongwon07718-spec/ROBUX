@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    print(f"{msg}")
    
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)
    
    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        
        key = f"{name}_{amount}"
        pending_deposits[key] = True
        print(f"✅ 이름({name}), 금액({amount})")
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            key = f"{fallback.group(1)}_{fallback.group(2)}"
            pending_deposits[key] = True
            print(f"✅: {key} (일반 포맷)")

    return {"ok": True}

def run_fastapi():
    """FastAPI 서버를 별도 스레드에서 실행"""
    uvicorn.run(app, host="0.0.0.0", port=88)
