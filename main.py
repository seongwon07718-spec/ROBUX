from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3, re, time, asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 충전 대기 목록 (중복 방지 및 만료 체크용)
# 구조: {"이름_금액": 입금시간(timestamp)}
pending_deposits = {}

class ChargeData(BaseModel):
    message: str
    server_id: str = ""
    pw: str = ""

# 입금 알림 수신 API (자동충전 봇 연동)
@app.post("/charge")
async def receive_charge(request: Request, data: ChargeData):
    # ID/PW 검증 로직 (생략 - 기존 코드 유지)
    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)

    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        key = f"{name}_{amount}"
        
        # 중복 방지 및 입금 처리
        pending_deposits[key] = time.time()
        return {"ok": True, "message": f"{name} / {int(amount):,}원 처리 완료"}
    
    raise HTTPException(status_code=400, detail="형식이 올바르지 않습니다.")

# 클라이언트 충전 상태 확인 API (Polling)
@app.get("/check_status/{name}/{amount}")
async def check_status(name: str, amount: str):
    key = f"{name}_{amount}"
    if key in pending_deposits:
        # 5분(300초) 경과 시 만료
        if time.time() - pending_deposits[key] > 300:
            del pending_deposits[key]
            return {"status": "expired"}
        return {"status": "success"}
    return {"status": "waiting"}

@app.get("/change", response_class=HTMLResponse)
async def change_page(request: Request):
    return templates.TemplateResponse("change.html", {"request": request})

@app.post("/change/api", response_class=HTMLResponse)
async def change_api(request: Request, depositor: str = Form(...), amount: str = Form(...)):
    return templates.TemplateResponse("change_api.html", {
        "request": request, 
        "name": depositor, 
        "amount": amount,
        "bank": {"owner": "정성원", "bank": "카카오뱅크", "account": "3333-01-2345678"}
    })
