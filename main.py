import sqlite3
import time
import io
import re
import uuid
import asyncio
import aiohttp
import multiprocessing
from threading import Thread

import discord
from discord import ui, app_commands
from discord.ext import commands
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

import database
import culture_logic

# ==========================================
# [ SECTION 1: FastAPI 서버 & 웹 뷰 ]
# ==========================================
app = FastAPI()

class ChargeData(BaseModel):
    message: str

pending_deposits = {}

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
        return HTMLResponse(content="<body style='background:#000;color:#fff;'><h2>데이터베이스 오류</h2></body>")
    
    if not res:
        return HTMLResponse(content="<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>데이터를 찾을 수 없습니다.</h2></body>")

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
            body {{ background-color: #0a0a0a; color: #ffffff; font-family: 'Pretendard', sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; }}
            .container {{ width: 90%; max-width: 450px; background: #141414; padding: 40px 30px; border-radius: 30px; text-align: center; border: 1px solid #222; box-shadow: 0 20px 40px rgba(0,0,0,0.4); }}
            h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 25px; word-break: break-all; }}
            .stock-label {{ font-size: 13px; color: #888; margin-bottom: 15px; display: block; }}
            .stock-box {{ background: #1f1f1f; padding: 25px; border-radius: 20px; border: 1px solid #333; text-align: center; white-space: pre-wrap; word-break: break-all; margin-bottom: 30px; color: #efefef; font-size: 16px; line-height: 1.6; }}
            .copy-btn {{ background: #ffffff; color: #000000; border: none; padding: 16px 0; width: 100%; font-size: 15px; font-weight: 700; border-radius: 15px; cursor: pointer; transition: all 0.2s ease; }}
            .copy-btn:hover {{ background: #e0e0e0; }}
            @media (max-width: 480px) {{ .container {{ padding: 35px 20px; }} }}
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
                tempTextArea.value = content; document.body.appendChild(tempTextArea); tempTextArea.select();
                try {{
                    document.execCommand('copy');
                    btn.innerText = '복사 완료'; btn.style.background = '#444'; btn.style.color = '#fff';
                    setTimeout(() => {{ btn.innerText = '텍스트 복사하기'; btn.style.background = '#ffffff'; btn.style.color = '#000000'; }}, 1500);
                }} catch (err) {{ alert('복사에 실패했습니다.'); }} finally {{ document.body.removeChild(tempTextArea); }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)
    
    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        key = f"{name}_{amount}"
        pending_deposits[key] = True
        print(f"✅ 입금감지: {key}")
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            key = f"{fallback.group(1)}_{fallback.group(2)}"
            pending_deposits[key] = True
            print(f"✅ 일반감지: {key}")
    return {"ok": True}

# ==========================================
# [ SECTION 2: 봇 설정 및 컨피그 ]
# ==========================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

BANK_CONFIG = {"bank_name": "카카오뱅크", "account_num": "7777-03-6763823", "owner": "정성원"}
WEBHOOK_CONFIG = {
    "업데이트": "https://discord.com/api/webhooks/1477700066243383538/a57t5MsuTDCRC9InxAF0d7K0fDhA-nkzgxE5EY7jkZ3M6FsDqppfU7zNW1rqSfl2XHMr",
    "후기": "https://discord.com/api/webhooks/1482568183599857714/GiNmRWBcAi-uEL4YLqx6xKas73k6sNIwoy8M0qIE1evWnNY6LG9Xcw-NHNX9Iyw5Sauc",
    "재고": "https://discord.com/api/webhooks/1483792903930384404/GghrAu5_jF5oQiC5bGEvce3cIQ0C6jqZzHaa8OXbVbU9lmlc6lBuakH3wzZbtlc9yU_o",
    "구매": "https://discord.com/api/webhooks/1483797346411217070/5RBW0XQlOcIRHNDYRB00unfp-Me6JrjU3UKRMbyDT6mzILuVVpx1dEJhCyzw3egC1CgQ"
}

AUTO_LOG_ENABLED = True
LOG_CHANNEL_ID = 1477980009753739325
CULTURE_COOKIE = ""

# ==========================================
# [ SECTION 3: 충전 시스템 (컬쳐랜드/모달) ]
# ==========================================
async def do_culture_charge(pin_string):
    try:
        cl = culture_logic.Cultureland(); await cl.login(CULTURE_COOKIE)
        target_pin = culture_logic.Pin(pin_string) 
        result_obj = await cl.charge_process([target_pin]); await cl.close()
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
            amount, u_id = res["amount"], str(it.user.id)
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount, amount, u_id))
            conn.commit(); conn.close()
            
            result_con.accent_color, result_con.add_item = 0x00ff00, ui.TextDisplay(f"## 충전 성공")
            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            result_con.add_item(ui.TextDisplay(f"**충전 금액:** {amount:,}원\n잔액이 정상적으로 반영되었습니다"))
            
            log_chan = self.bot.get_channel(self.log_channel_id)
            if log_chan:
                log_con = ui.Container(ui.TextDisplay(f"## 문상 충전로그"), accent_color=0x00ff00)
                log_con.add_item(ui.TextDisplay(f"**신청자:** {it.user.mention}\n**충전금액:** {amount:,}원\n**상태:** 자동 승인 완료"))
                await log_chan.send(view=ui.LayoutView().add_item(log_con))
        else:
            reason = res.get("message", "잘못된 핀번호이거나 이미 사용된 번호입니다")
            result_con.accent_color, result_con.add_item = 0xff0000, ui.TextDisplay(f"## 충전 실패")
            result_con.add_item(ui.TextDisplay(f"**사유:** {reason}"))
        
        await it.edit_original_response(view=ui.LayoutView().add_item(result_con))

# ==========================================
# [ SECTION 4: 구매 및 후기 시스템 ]
# ==========================================
class ReviewModal(ui.Modal, title="구매 후기 작성"):
    rating = ui.TextInput(label="별점", placeholder="숫자 1~5 입력 (예: 5)", min_length=1, max_length=1)
    content = ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, placeholder="솔직한 후기를 남겨주세요", min_length=5, max_length=200)

    def __init__(self, prod_name):
        super().__init__(); self.prod_name = prod_name

    async def on_submit(self, it: discord.Interaction):
        if not self.rating.value.isdigit() or not (1 <= int(self.rating.value) <= 5):
            return await it.response.send_message("**별점은 1에서 5 사이의 숫자만 입력 가능합니다**", ephemeral=True)

        stars = "⭐️" * int(self.rating.value)
        review_con = ui.Container(ui.TextDisplay(f"## 구매 후기"), accent_color=0xffffff)
        review_con.add_item(ui.TextDisplay(f"구매자: {it.user.mention}\n제품: {self.prod_name}\n별점: {stars}"))
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"```{self.content.value}```"))

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_CONFIG["후기"], session=session)
            await webhook.send(view=ui.LayoutView().add_item(review_con), username="Service Review")
        await it.response.send_message("**후기가 성공적으로 등록되었습니다**", ephemeral=True)

class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name, self.price, self.stock = prod_name, price, stock
        self.count = ui.TextInput(label="구매 수량", placeholder="수량을 입력하세요", min_length=1, max_length=5)
        self.add_item(self.count)

    async def send_purchase_webhook(self, user, prod_name, count, price):
        log_con = ui.Container(ui.TextDisplay("## 구매 로그 알림"), accent_color=0xffffff)
        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> {user}님 {prod_name} / {count}개 구매 감사합니다"))
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_CONFIG["구매"], session=session)
                await webhook.send(view=ui.LayoutView().add_item(log_con))
        except Exception as e: print(f"구매 로그 실패: {e}")

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("숫자로만 입력해주세요.", ephemeral=True)
        
        buy_count, total_price, u_id = int(self.count.value), self.price * int(self.count.value), str(it.user.id)
        
        wait_con = ui.Container(ui.TextDisplay("## 구매 진행 중"), accent_color=0xffff00)
        wait_con.add_item(ui.TextDisplay(f"**<a:027:1482026501279977574> 구매 처리 진행중입니다**"))
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)
        await asyncio.sleep(3.0)

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        user_money = (cur.fetchone() or (0,))[0]
        res_con = ui.Container()
        
        if buy_count > self.stock or user_money < total_price:
            res_con.accent_color, res_con.add_item = 0xff0000, ui.TextDisplay("## 구매 실패")
            res_con.add_item(ui.TextDisplay("재고 혹은 잔액이 부족합니다."))
            conn.close(); return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("SELECT stock_data FROM products WHERE name = ?", (self.prod_name,))
        stock_list = (cur.fetchone()[0] or "").split('\n')
        delivery_items, remaining_stock = stock_list[:buy_count], "\n".join(stock_list[buy_count:])
        
        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ?, sold_count = sold_count + ?, stock_data = ? WHERE name = ?", (buy_count, buy_count, remaining_stock, self.prod_name))
        
        web_key = str(uuid.uuid4())
        cur.execute("INSERT INTO buy_log (user_id, product_name, stock_data, date, web_key) VALUES (?, ?, ?, ?, ?)", (u_id, self.prod_name, "\n".join(delivery_items), time.strftime('%Y-%m-%d %H:%M'), web_key))
        conn.commit(); conn.close()

        await self.send_purchase_webhook(it.user, self.prod_name, buy_count, total_price)
        res_con.accent_color, res_con.add_item = 0x00ff00, ui.TextDisplay(f"## 구매 완료")
        res_con.add_item(ui.TextDisplay(f"제품명: {self.prod_name}\n수량: {buy_count}개\n차감: {total_price:,}원"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            view_url = f"http://buy.swnx.shop/view?key={web_key}"
            dm_con = ui.Container(ui.TextDisplay("## 구매 제품"), accent_color=0xffffff)
            dm_con.add_item(ui.TextDisplay(f"제품명: {self.prod_name}\n수량: {buy_count}개\n결제액: {total_price:,}원"))
            
            review_btn = ui.Button(label="후기작성", style=discord.ButtonStyle.gray, emoji="<:bel:1482196301578764308>")
            review_btn.callback = lambda it_btn: it_btn.response.send_modal(ReviewModal(self.prod_name))
            view_btn = ui.Button(label="제품보기", url=view_url, style=discord.ButtonStyle.link, emoji="<:shop:1481994009499930766>")
            
            dm_con.add_item(ui.ActionRow(review_btn, view_btn))
            await it.user.send(view=ui.LayoutView().add_item(dm_con))
        except Exception as e: print(f"DM 전송 실패: {e}")
