import discord
import asyncio
import aiohttp
from discord import ui
from discord.ext import commands
from discord import app_commands
import database
import time
import culture_logic
import sqlite3
import re
import io
import uvicorn  
import uuid
from fastapi.responses import HTMLResponse
import uvicorn
import multiprocessing
from fastapi import FastAPI, Request 
from pydantic import BaseModel  
from threading import Thread 

app = FastAPI()

class ChargeData(BaseModel):
    message: str

pending_deposits = {}

# 제품 웹 사이트 디자인
@app.get("/view")
async def view_product(key: str = None):
    if not key:
        return HTMLResponse(content="<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>잘못된 접근입니다.</h2></body>")

    try:
        conn = sqlite3.connect('vending_data.db', timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT product_name, stock_data FROM buy_log WHERE web_key = ?", (key,))
        res = cur.fetchone()
        conn.close()
    except Exception as e:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;'><h2>데이터베이스 오류</h2></body>")
    
    if not res:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>데이터를 찾을 수 없습니다.</h2></body>")

    prod_name, stock_data = res

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>구매 정보 확인</title>
        <style>
            @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
            
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                background-color: #0a0a0a; 
                color: #ffffff; 
                font-family: 'Pretendard', sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                width: 100%;
            }}
            .container {{ 
                width: 90%; 
                max-width: 450px; 
                background: #141414;
                padding: 40px 30px; 
                border-radius: 30px; /* 외곽 컨테이너 둥글게 */
                text-align: center; 
                border: 1px solid #222;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            }}
            h1 {{ 
                font-size: 24px; 
                font-weight: 700; 
                margin-bottom: 25px;
                word-break: break-all;
            }}
            .stock-label {{
                font-size: 13px;
                color: #888;
                margin-bottom: 15px;
                display: block;
            }}
            .stock-box {{ 
                background: #1f1f1f; 
                padding: 25px; 
                border-radius: 20px; /* 내부 박스 둥글게 */
                border: 1px solid #333; 
                text-align: center; 
                font-family: 'Pretendard', sans-serif; 
                white-space: pre-wrap; 
                word-break: break-all; 
                margin-bottom: 30px; 
                color: #efefef; 
                font-size: 16px; 
                line-height: 1.6;
            }}
            .copy-btn {{ 
                background: #ffffff; 
                color: #000000; 
                border: none; 
                padding: 16px 0; 
                width: 100%; 
                font-size: 15px; 
                font-weight: 700; 
                border-radius: 15px; /* 버튼 둥글게 */
                cursor: pointer; 
                transition: all 0.2s ease; 
            }}
            .copy-btn:hover {{ 
                background: #e0e0e0; 
            }}
            .copy-btn:active {{
                transform: scale(0.97);
            }}

            @media (max-width: 480px) {{
                .container {{ padding: 35px 20px; }}
                h1 {{ font-size: 22px; }}
                .stock-box {{ font-size: 15px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{prod_name}</h1>
            
            <span class="stock-label">상품 정보</span>
            <div class="stock-box" id="stockContent">{stock_data}</div>
            
            <button class="copy-btn" id="copyBtn" onclick="copyToClipboard()">텍스트 복사하기</button>
        </div>

        <script>
            function copyToClipboard() {{
                const content = document.getElementById('stockContent').innerText;
                const btn = document.getElementById('copyBtn');
                
                const tempTextArea = document.createElement('textarea');
                tempTextArea.value = content;
                document.body.appendChild(tempTextArea);
                tempTextArea.select();
                
                try {{
                    document.execCommand('copy');
                    btn.innerText = '복사 완료';
                    btn.style.background = '#444';
                    btn.style.color = '#fff';
                    setTimeout(() => {{
                        btn.innerText = '텍스트 복사하기';
                        btn.style.background = '#ffffff';
                        btn.style.color = '#000000';
                    }}, 1500);
                }} catch (err) {{
                    alert('복사에 실패했습니다.');
                }} finally {{
                    document.body.removeChild(tempTextArea);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# IOS 자동충전
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

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 충전 계좌
BANK_CONFIG = {
    "bank_name": "카카오뱅크",
    "account_num": "7777-03-6763823",
    "owner": "정성원"
}

# 서버 웹훅
WEBHOOK_CONFIG = {
    "업데이트": "https://discord.com/api/webhooks/1477700066243383538/a57t5MsuTDCRC9InxAF0d7K0fDhA-nkzgxE5EY7jkZ3M6FsDqppfU7zNW1rqSfl2XHMr",
    "후기": "https://discord.com/api/webhooks/1482568183599857714/GiNmRWBcAi-uEL4YLqx6xKas73k6sNIwoy8M0qIE1evWnNY6LG9Xcw-NHNX9Iyw5Sauc",
    "재고": "https://discord.com/api/webhooks/1483792903930384404/GghrAu5_jF5oQiC5bGEvce3cIQ0C6jqZzHaa8OXbVbU9lmlc6lBuakH3wzZbtlc9yU_o",
    "구매": "https://discord.com/api/webhooks/1483797346411217070/5RBW0XQlOcIRHNDYRB00unfp-Me6JrjU3UKRMbyDT6mzILuVVpx1dEJhCyzw3egC1CgQ"
}

# 기초 설정
AUTO_LOG_ENABLED = True
LOG_CHANNEL_ID = 1477980009753739325

# 문상 자충 쿠키
CULTURE_COOKIE = ""

# 문상 자충 (현재 안됨 수정 필요)
async def do_culture_charge(pin_string):
    try:
        cl = culture_logic.Cultureland()
        await cl.login(CULTURE_COOKIE)
        target_pin = culture_logic.Pin(pin_string) 
        result_obj = await cl.charge_process([target_pin]) 
        await cl.close()
        final_res = result_obj[0] if isinstance(result_obj, list) else result_obj
        return {"status": "success" if final_res.amount > 0 else "error", "amount": final_res.amount, "message": final_res.message}
    except Exception as e:
        print(f"❌ [컬쳐랜드 에러]: {e}"); return {"status": "error", "message": str(e)}

class CultureModal(ui.Modal, title="문상 정보"):
    pin = ui.TextInput(label="핀번호 입력", placeholder="하이픈(-) 없이 숫자만 입력하세요", min_length=16, max_length=19)
    def __init__(self, bot, log_channel_id):
        super().__init__(); self.bot = bot; self.log_channel_id = log_channel_id
    async def on_submit(self, it: discord.Interaction):
        wait_con = ui.Container(ui.TextDisplay("## 핀번호 확인 중"), ui.TextDisplay("약 5~10초 정도 소요됩니다\n잠시만 기다려 주세요"), accent_color=0xffff00)
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)
        clean_pin = str(self.pin.value).replace("-", "").strip()
        res = await do_culture_charge(clean_pin)
        result_con = ui.Container()
        if res["status"] == "success" and res.get("amount", 0) > 0:
            amount = res["amount"]; u_id = str(it.user.id)
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount, amount, u_id))
            conn.commit(); conn.close()
            result_con.accent_color = 0x00ff00; result_con.add_item(ui.TextDisplay(f"## 충전 성공"))
            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            result_con.add_item(ui.TextDisplay(f"**충전 금액:** {amount:,}원\n잔액이 정상적으로 반영되었습니다"))
            log_chan = self.bot.get_channel(self.log_channel_id)
            if log_chan:
                log_con = ui.Container(ui.TextDisplay(f"## 문상 충전로그"), accent_color=0x00ff00)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                log_con.add_item(ui.TextDisplay(f"**신청자:** {it.user.mention}\n**충전금액:** {amount:,}원\n**상태:** 자동 승인 완료"))
                await log_chan.send(view=ui.LayoutView().add_item(log_con))
        else:
            reason = res.get("message", "잘못된 핀번호이거나 이미 사용된 번호입니다")
            result_con.accent_color = 0xff0000; result_con.add_item(ui.TextDisplay(f"## 충전 실패"))
            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            result_con.add_item(ui.TextDisplay(f"**사유:** {reason}"))
        await it.edit_original_response(view=ui.LayoutView().add_item(result_con))

class ReviewModal(ui.Modal, title="구매 후기 작성"):
    rating = ui.TextInput(label="별점", placeholder="숫자 1~5 입력 (예: 5)", min_length=1, max_length=1)
    content = ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, placeholder="솔직한 후기를 남겨주세요", min_length=5, max_length=200)

    def __init__(self, prod_name):
        super().__init__()
        self.prod_name = prod_name

    async def on_submit(self, it: discord.Interaction):
        if not self.rating.value.isdigit() or not (1 <= int(self.rating.value) <= 5):
            return await it.response.send_message("**별점은 1에서 5 사이의 숫자만 입력 가능합니다**", ephemeral=True)

        stars = "⭐️" * int(self.rating.value)
        review_url = WEBHOOK_CONFIG.get("후기")

        review_con = ui.Container(ui.TextDisplay(f"## 구매 후기"), accent_color=0xffffff)
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"구매자: {it.user.mention}\n제품: {self.prod_name}\n별점: {stars}"))
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"```{self.content.value}```"))

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(review_url, session=session)
            await webhook.send(view=ui.LayoutView().add_item(review_con), username="Service Review")

        await it.response.send_message("**후기가 성공적으로 등록되었습니다**", ephemeral=True)

class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name = prod_name
        self.price = price
        self.stock = stock
        
        self.count = ui.TextInput(
            label="구매 수량", 
            placeholder="수량을 입력하세요", 
            min_length=1, 
            max_length=5
        )
        self.add_item(self.count)

    async def send_purchase_webhook(self, user, prod_name, count, price):
        
        Purchase_url = WEBHOOK_CONFIG["구매"]

        log_con = ui.Container(ui.TextDisplay("## 구매 로그 알림"), accent_color=0xffffff)
        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        log_con.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> {user}님 {prod_name} / {count}개 구매 감사합니다"
        ))
        
        log_v = ui.LayoutView().add_item(log_con)
        
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(Purchase_url, session=session)
                await webhook.send(view=log_v)
        except Exception as e:
            print(f"구매 로그 웹훅 전송 실패: {e}")

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True) 
        if not self.count.value.isdigit():
            err_con = ui.Container(ui.TextDisplay("## ❌ 입력 오류"), accent_color=0xff0000)
            err_con.add_item(ui.TextDisplay("숫자로만 입력해주세요."))
            return await it.response.send_message(view=ui.LayoutView().add_item(err_con), ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        wait_con = ui.Container(ui.TextDisplay("## 구매 진행 중"), accent_color=0xffff00)
        wait_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        wait_con.add_item(ui.TextDisplay(f"**<a:027:1482026501279977574>  구매 처리 진행중입니다**"))
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)

        await asyncio.sleep(3.0)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        user_money_res = cur.fetchone()
        user_money = user_money_res[0] if user_money_res else 0

        res_con = ui.Container()
        
        if buy_count > self.stock:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## 재고 부족"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"(현재 재고: {self.stock}개)"))
            conn.close()
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        
        if user_money < total_price:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## 잔액 부족"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"(필요: {total_price:,}원 / 보유: {user_money:,}원)"))
            conn.close()
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("SELECT stock_data FROM products WHERE name = ?", (self.prod_name,))
        stock_res = cur.fetchone()
        stock_list = stock_res[0].split('\n') if stock_res and stock_res[0] else []
        
        delivery_items = stock_list[:buy_count]
        purchased_stock_text = "\n".join(delivery_items) 
        remaining_stock_data = "\n".join(stock_list[buy_count:])

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("""UPDATE products 
                       SET stock = stock - ?, 
                           sold_count = sold_count + ?, 
                           stock_data = ? 
                       WHERE name = ?""", (buy_count, buy_count, remaining_stock_data, self.prod_name))
        
        web_key = str(uuid.uuid4())
        
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)",
                    (u_id, self.prod_name, purchased_stock_text, time.strftime('%Y-%m-%d %H:%M'), web_key))
        conn.commit()
        conn.close()

        await self.send_purchase_webhook(it.user, self.prod_name, buy_count, total_price)

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay(f"## 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n<:dot_white:1482000567562928271> 구매 수량: {buy_count}개\n<:dot_white:1482000567562928271> 차감 금액: {total_price:,}원"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay("-# DM으로 제품 전송되었습니다"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            domain = "buy.swnx.shop" 
            view_url = f"http://{domain}/view?key={web_key}"

            dm_con = ui.Container(ui.TextDisplay("## 구매 제품"), accent_color=0xffffff)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(
                f"<:dot_white:1482000567562928271> 제품명: {self.prod_name}\n"
                f"<:dot_white:1482000567562928271> 구매수량: {buy_count}개\n"
                f"<:dot_white:1482000567562928271> 결제금액: {total_price:,}원\n"
                f"<:dot_white:1482000567562928271> 남은 잔액: {user_money - total_price:,}원"
            ))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            review_btn = ui.Button(label="후기작성", style=discord.ButtonStyle.gray, emoji="<:bel:1482196301578764308>")
            async def review_btn_callback(it_btn: discord.Interaction):
                await it_btn.response.send_modal(ReviewModal(self.prod_name))
            review_btn.callback = review_btn_callback
            
            view_btn = ui.Button(
                label="제품보기", 
                url=view_url, 
                style=discord.ButtonStyle.link,
                emoji="<:shop:1481994009499930766>"
            )
            
            dm_con.add_item(ui.ActionRow(review_btn, view_btn))
            
            dm_v = ui.LayoutView().add_item(dm_con)
            await it.user.send(view=dm_v)

        except Exception as e:
            print(f"DM 전송 실패: {e}")
