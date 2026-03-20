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

class CategorySelect(ui.Select):
    def __init__(self):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        super().__init__(placeholder="카테고리를 선택하세요", options=options, min_values=1, max_values=1)

class ProductSelect(ui.Select):
    def __init__(self, category):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        super().__init__(placeholder="제품을 선택하세요", options=options, min_values=1, max_values=1)

class ProductEditModal(ui.Modal):
    def __init__(self, category, prod_name):
        super().__init__(title=f"제품 수정: {prod_name}")
        self.category = category
        self.old_name = prod_name
        
        self.name_input = ui.TextInput(label="제품 이름", default=prod_name)
        self.price_input = ui.TextInput(label="가격", placeholder="숫자만 입력")
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        if res: self.price_input.placeholder = f"현재 가격: {res[0]}원"

        self.add_item(self.name_input)
        self.add_item(self.price_input)

    async def on_submit(self, it: discord.Interaction):
        new_price = self.price_input.value
        if new_price and not new_price.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력 가능합니다**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        if new_price:
            cur.execute("UPDATE products SET name = ?, price = ? WHERE name = ?", (self.name_input.value, int(new_price), self.old_name))
        else:
            cur.execute("UPDATE products SET name = ? WHERE name = ?", (self.name_input.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{self.old_name}__ 제품 정보가 수정되었습니다**", ephemeral=True)

class CategorySelectView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        self.container = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none":
            return await it.response.send_message("**선택 가능한 카테고리가 없습니다**", ephemeral=True)
        
        await it.response.send_modal(ProductEditModal(selected_cat))

class NewProductModal(ui.Modal, title="신규 상품 등록"):
    cat = ui.TextInput(label="카테고리", placeholder="카테고리를 적어주세요")
    name = ui.TextInput(label="제품명", placeholder="등록할 제품 이름을 적어주세요")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력해주세요")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력해 주세요**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                    (self.cat.value, self.name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"**__{self.name.value}__ 등록 완료되었습니다**", ephemeral=True)

class CategoryDeleteModal(ui.Modal, title="카테고리 삭제"):
    def __init__(self):
        super().__init__()
        self.cat_select = ui.Label(
            text="삭제할 카테고리를 선택하세요",
            component=CategorySelect()
        )
        self.add_item(self.cat_select)

    async def on_submit(self, it: discord.Interaction):
        cat_name = self.cat_select.component.values[0]
        if cat_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE category = ?", (cat_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 __[{cat_name}]__ 및 포함된 모든 제품이 삭제되었습니다**", ephemeral=True)

class CategorySelectView(ui.LayoutView):
    def __init__(self, purpose="edit"):
        super().__init__(timeout=60)
        self.purpose = purpose
        title = "제품 삭제 - 카테고리 선택" if purpose == "delete" else "상품 설정 - 카테고리 선택"
        self.container = ui.Container(ui.TextDisplay(f"## {title}"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none": return
        
        if self.purpose == "delete":
            await it.response.send_modal(ProductDeleteModal(selected_cat))
        else:
            await it.response.send_modal(ProductEditModal(selected_cat))

class ProductDeleteModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 삭제")
        self.prod_select = ui.Label(
            text=f"삭제할 {category} 제품을 선택하세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_select)

    async def on_submit(self, it: discord.Interaction):
        prod_name = self.prod_select.component.values[0]
        if prod_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE name = ?", (prod_name,))
        conn.commit(); conn.close()
        await it.response.send_message(f"**제품 __[{prod_name}]__이(가) 성공적으로 삭제되었습니다**", ephemeral=True)

class StockCategorySelectView(ui.LayoutView):
    def __init__(self, category=None):
        super().__init__(timeout=60)
        self.category = category
        
        if not self.category:
            self.con = ui.Container(ui.TextDisplay("## 재고 수정 - 카테고리 선택"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.add_category_select()
        else:
            self.con = ui.Container(ui.TextDisplay(f"## [{self.category}] 제품 선택"), accent_color=0xffffff)
            self.con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.add_product_select()

        self.add_item(self.con)

    def add_category_select(self):
        """카테고리 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        select = ui.Select(placeholder="카테고리 선택하기", options=options)
        select.callback = self.category_callback
        self.con.add_item(ui.ActionRow(select))

    def add_product_select(self):
        """제품 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (self.category,))
        prods = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        select = ui.Select(placeholder="제품 선택하기", options=options)
        select.callback = self.product_callback
        self.con.add_item(ui.ActionRow(select))

    async def category_callback(self, it: discord.Interaction):
        selected = it.data['values'][0]
        if selected == "none": return
        
        new_view = StockCategorySelectView(category=selected)
        await it.response.edit_message(view=new_view)

    async def product_callback(self, it: discord.Interaction):
        prod_name = it.data['values'][0]
        if prod_name == "none": return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        current_data = res[0] if res and res[0] else ""
        
        await it.response.send_modal(StockDataListModal(prod_name, current_data))

async def stock_edit_product_callback(self, it: discord.Interaction):
    prod_name = it.data['values'][0]
    if prod_name == "none": return
    
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
    res = cur.fetchone()
    conn.close()
    
    current_stock_list = res[0] if res and res[0] else ""
    
    await it.response.send_modal(StockDataListModal(prod_name, current_stock_list))

class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"{name} 재고 관리")
        self.name = name
        
        self.data_input = ui.TextInput(
            label="재고 리스트",
            style=discord.TextStyle.paragraph,
            default=str(current_data),
            placeholder="재고가 비어있습니다", 
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        
        cur.execute("SELECT stock FROM products WHERE name = ?", (self.name,))
        old_res = cur.fetchone()
        old_count = old_res[0] if old_res else 0

        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit()
        conn.close()
        
        if new_count > old_count:
            await self.send_stock_webhook_container(self.name, new_count, new_count - old_count)

        await it.response.send_message(f"**__{self.name}__ 재고 수정 완료되었습니다 (현재: __{new_count}__개)**", ephemeral=True)

    async def send_stock_webhook_container(self, name, total_count, added_count):
        
        stock_url = WEBHOOK_CONFIG.get("재고")

        stock_con = ui.Container(ui.TextDisplay("## 제품 입고 알림"), accent_color=0xffffff)
        stock_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        stock_con.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 제품명: {name}\n"
            f"<:dot_white:1482000567562928271> 입고 수량: {added_count}개\n"
            f"<:dot_white:1482000567562928271> 현재 총 재고: {total_count}개"
        ))
        
        stock_v = ui.LayoutView().add_item(stock_con)
        
        try:
            webhook = discord.Webhook.from_url(stock_url, session=aiohttp.ClientSession())
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(stock_url, session=session)
                await webhook.send(view=stock_v)
        except Exception as e:
            print(f"웹훅 컨테이너 전송 실패: {e}")

class CategoryEditModal(ui.Modal, title="카테고리 이름 수정"):
    def __init__(self, old_name):
        super().__init__()
        self.old_name = old_name
        self.new_name = ui.TextInput(label="새 카테고리 이름", default=old_name, placeholder="변경할 이름을 입력하세요")
        self.add_item(self.new_name)

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET category = ? WHERE category = ?", (self.new_name.value, self.old_name))
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리명이 __{self.old_name}__에서 __{self.new_name.value}__(으)로 변경되었습니다.**", ephemeral=True)

class AddProductModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"[{category}] 제품 추가")
        self.category = category
        self.name = ui.TextInput(label="제품명", placeholder="추가할 제품 이름을 적어주세요")
        self.price = ui.TextInput(label="가격", placeholder="숫자만 입력해주세요")
        self.add_item(self.name); self.add_item(self.price)

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("**가격은 숫자만 입력해 주세요**", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock, sold_count) VALUES (?, ?, ?, ?, ?)",
                    (self.category, self.name.value, int(self.price.value), 0, 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"**[{self.category}]**에 **__{self.name.value}__** 등록 완료되었습니다.", ephemeral=True)

class AddCategoryModal(ui.Modal, title="신규 카테고리 추가"):
    cat_name = ui.TextInput(label="카테고리 이름", placeholder="생성할 카테고리 이름을 적어주세요")

    async def on_submit(self, it: discord.Interaction):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        
        cur.execute("SELECT DISTINCT category FROM products WHERE category = ?", (self.cat_name.value,))
        if cur.fetchone():
            conn.close()
            return await it.response.send_message(f"**이미 존재하는 카테고리입니다: {self.cat_name.value}**", ephemeral=True)
        
        conn.commit(); conn.close()
        await it.response.send_message(f"**카테고리 __{self.cat_name.value}__ 등록이 완료되었습니다**", ephemeral=True)

class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("상품 관리를 원하시면 드롭바를 눌러 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.admin_select = ui.Select(
            placeholder="관리 항목을 선택해주세요",
            options=[
                discord.SelectOption(label="제품 추가", value="add_prod", description="카테고리를 선택하여 제품을 추가합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 삭제", value="del_prod", description="카테고리를 선택하여 제품을 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="제품 수정", value="edit_prod", description="제품의 이름과 가격을 수정합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="재고 수정", value="stock_edit", description="제품의 재고 데이터를 수정합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 추가", value="add_cat", description="카테고리를 추가합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 삭제", value="del_cat", description="카테고리와 제품을 전체 삭제합니다", emoji="<:dot_white:1482000567562928271>"),
                discord.SelectOption(label="카테고리 수정", value="edit_cat", description="카테고리 이름을 수정합니다", emoji="<:dot_white:1482000567562928271>"),
            ]
        )
        self.admin_select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.admin_select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        val = self.admin_select.values[0]
        
        if val == "add_cat":
            await it.response.send_modal(AddCategoryModal())
            
        elif val == "add_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="add"), ephemeral=True)
            
        elif val == "edit_cat":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_cat"), ephemeral=True)
            
        elif val == "edit_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_prod"), ephemeral=True)
            
        elif val == "del_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="delete_prod"), ephemeral=True)
            
        elif val == "del_cat":
            await it.response.send_modal(CategoryDeleteModal())
            
        elif val == "stock_edit":
            await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)

class AdminCategorySelectView(ui.LayoutView):
    def __init__(self, purpose):
        super().__init__(timeout=60)
        self.purpose = purpose
        titles = {
            "add": "제품 추가 - 카테고리 선택",
            "edit_cat": "카테고리 수정 - 카테고리 선택",
            "edit_prod": "제품 수정 - 카테고리 선택",
            "delete_prod": "제품 삭제 - 카테고리 선택"
        }
        self.container = ui.Container(ui.TextDisplay(f"## {titles.get(purpose)}"), accent_color=0xffffff)
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none": return

        if self.purpose == "add":
            await it.response.send_modal(AddProductModal(selected_cat))
        elif self.purpose == "edit_cat":
            await it.response.send_modal(CategoryEditModal(selected_cat))
        elif self.purpose == "edit_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 수정할 제품 선택"), accent_color=0xffffff)
            new_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_sel = ProductSelect(selected_cat)
            async def ps_callback(it2: discord.Interaction):
                await it2.response.send_modal(ProductEditModal(selected_cat, prod_sel.values[0]))
            prod_sel.callback = ps_callback
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))
        elif self.purpose == "delete_prod":
            new_con = ui.Container(ui.TextDisplay(f"## [{selected_cat}] 삭제할 제품 선택"), accent_color=0xffffff)
            new_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_sel = ProductSelect(selected_cat)
            prod_sel.callback = lambda i: it.response.send_modal(ProductDeleteModal(selected_cat))
            new_con.add_item(ui.ActionRow(prod_sel))
            await it.response.edit_message(view=ui.LayoutView().add_item(new_con))

class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(); self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 신청자: {user.mention}\n<:dot_white:1482000567562928271> 입금자명: {name}\n<:dot_white:1482000567562928271> 신청금액: {amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        approve_btn = ui.Button(label="완료", emoji="<:UpArrow:1482008374777483324>"); approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", emoji="<:DownArrow:1482008377482678335>"); cancel_btn.callback = self.cancel_callback
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn)); self.add_item(self.container)

    async def approve_callback(self, interaction: discord.Interaction):
        amount_int = int(self.amount)
        u_id = str(self.user.id)
        
        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "수동(관리자)"))
        conn.commit()
        conn.close()

        database.update_status(self.db_id, "완료")
        self.container.clear_items()
        self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 처리자: {interaction.user.mention}\n<:dot_white:1482000567562928271> 대상: {self.user.mention}\n<:dot_white:1482000567562928271> 금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 성공적으로 결과가 처리되었습니다"))
        
        await interaction.response.edit_message(view=self)
        
        try: 
            dm_con = ui.Container(ui.TextDisplay("## 충전 완료"), accent_color=0x00ff00)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> {self.amount}원 충전이 완료되었습니다"))
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay("-# 저의 서버를 이용해주셔서 감사합니다"))
            await self.user.send(view=ui.LayoutView().add_item(dm_con))
        except: 
            pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 처리자: {interaction.user.mention}\n<:dot_white:1482000567562928271> 대상: {self.user.mention}\n<:dot_white:1482000567562928271> 금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 성공적으로 결과가 처리되었습니다"))
        await interaction.response.edit_message(view=self)

class AccountSetupModal(ui.Modal, title="계좌 정보 설정"):
    bank = ui.TextInput(label="은행명", placeholder="예: 카카오뱅크", min_length=2)
    account = ui.TextInput(label="계좌번호", placeholder="하이픈 포함 입력")
    owner = ui.TextInput(label="예금주", placeholder="성함 입력")

    async def on_submit(self, interaction: discord.Interaction):
        global AUTO_LOG_ENABLED
        BANK_CONFIG["bank_name"] = self.bank.value
        BANK_CONFIG["account_num"] = self.account.value
        BANK_CONFIG["owner"] = self.owner.value

        setup_con = ui.Container(ui.TextDisplay("## 계좌 설정 완료"), accent_color=0x00ff00)
        setup_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        setup_con.add_item(ui.TextDisplay(f"은행: {self.bank.value}\n계좌: {self.account.value}\n예금주: {self.owner.value}"))
        
        view = ui.LayoutView()
        
        if "카카오뱅크" in self.bank.value or "카뱅" in self.bank.value:
            allow_btn = ui.Button(label="자동충전 허용", style=discord.ButtonStyle.green)
            deny_btn = ui.Button(label="자동충전 거부", style=discord.ButtonStyle.red)
            
            async def allow_cb(it):
                global AUTO_LOG_ENABLED
                AUTO_LOG_ENABLED = False
                await it.response.send_message("**자동충전이 허용되었습니다 (로그 미발송)**", ephemeral=True)
            
            async def deny_cb(it):
                global AUTO_LOG_ENABLED
                AUTO_LOG_ENABLED = True
                await it.response.send_message("**자동충전이 거부되었습니다 (로그 발송)**", ephemeral=True)
            
            allow_btn.callback = allow_cb
            deny_btn.callback = deny_cb
            setup_con.add_item(ui.ActionRow(allow_btn, deny_btn))
        
        view.add_item(setup_con)
        await interaction.response.send_message(view=view, ephemeral=True)

class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 은행명: {BANK_CONFIG['bank_name']}\n<:dot_white:1482000567562928271> 계좌번호: {BANK_CONFIG['account_num']}\n<:dot_white:1482000567562928271> 예금주: {BANK_CONFIG['owner']}\n<:dot_white:1482000567562928271> 충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 자동충전됩니다"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        self.copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:copy:1482673389679415316>")
        self.copy_btn.callback = self.copy_callback
        
        self.container.add_item(ui.ActionRow(self.copy_btn))
        self.add_item(self.container)

    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)
        if database.get_status(self.db_id) == "대기":
            self.container.clear_items(); self.container.accent_color = 0xff0000
            self.container.add_item(ui.TextDisplay("## 충전 시간 초과")); self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.container.add_item(ui.TextDisplay("자동충전 시간이 초과되었습니다"))
            await interaction.edit_original_response(view=self)

    async def copy_callback(self, it: discord.Interaction):
        self.copy_btn.disabled = True
        await it.response.edit_message(view=self)
        await it.followup.send(content=f"{BANK_CONFIG['account_num']}", ephemeral=True)

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요 (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        if AUTO_LOG_ENABLED:
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan: 
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        name_val = self.name.value
        amount_val = self.amount.value
        key = f"{name_val}_{amount_val}"
        asyncio.create_task(self.watch_deposit(interaction, layout, name_val, amount_val, key))

    async def watch_deposit(self, interaction, layout, name, amount, key):
        start_time = time.time()
        while True:
            if time.time() - start_time > 300:
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "시간초과")
                layout.container.clear_items()
                layout.container.accent_color = 0xff0000
                layout.container.add_item(ui.TextDisplay("## 입금 시간 초과"))
                layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                layout.container.add_item(ui.TextDisplay("5분 이내에 입금이 확인되지 않아 취소되었습니다"))
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

            await asyncio.sleep(3)
            if pending_deposits.get(key):
                amount_int = int(amount)
                u_id = str(interaction.user.id)
                conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
                cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
                cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                            (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "자동(계좌)"))
                conn.commit(); conn.close()
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "완료")

                layout.container.clear_items()
                layout.container.accent_color = 0x00ff00
                layout.container.add_item(ui.TextDisplay("## 충전 완료"))
                layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                layout.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 충전금액: {amount_int:,}원"))
                layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                layout.container.add_item(ui.TextDisplay("-# 성공적으로 충전이 완료되었습니다"))
                    
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small)); container.add_item(ui.TextDisplay("원하시는 충전 수단을 선택해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray, emoji="<:dot_white:1482000567562928271>"); bank.callback = self.bank_callback
        gift_card = ui.Button(label="문상결제", style=discord.ButtonStyle.gray, emoji="<:dot_white:1482000567562928271>"); gift_card.callback = self.gift_card_callback
        container.add_item(ui.ActionRow(bank, gift_card)); self.add_item(container)
    async def bank_callback(self, it): await it.response.send_modal(BankModal())
    async def gift_card_callback(self, it): await it.response.send_modal(CultureModal(bot, LOG_CHANNEL_ID))

async def check_black(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    cur.execute("SELECT is_blacked FROM users WHERE user_id = ?", (u_id,))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0] == 1:
        return True 
    return False

class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) 
        self.container = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌려 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        buy = ui.Button(label="구매", emoji="<:buy:1481994292255002705>")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="제품", emoji="<:shop:1481994009499930766>")
        shop.callback = self.shop_callback
        
        chage = ui.Button(label="충전", emoji="<:change:1481994723802611732>")
        chage.callback = self.chage_callback
        
        info = ui.Button(label="정보", emoji="<:info:1481993647774892043>")
        info.callback = self.info_callback
        
        self.container.add_item(ui.ActionRow(buy, shop, chage, info))
        self.add_item(self.container)

    async def info_callback(self, it: discord.Interaction):
        if await check_black(it): return
        
        u_id = str(it.user.id)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        money, total_spent = (row[0], row[1]) if row else (0, 0)
        
        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 보유 잔액: {money:,}원\n<:dot_white:1482000567562928271> 누적 금액: {total_spent:,}원"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:dot_white:1482000567562928271>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:dot_white:1482000567562928271>")
        ])

        async def resp_callback(i: discord.Interaction):
            selected_val = selecao.values[0]
            conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
            
            if selected_val == "charge":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount > 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {l[0]:,}원 ({l[2]})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("충전 내역이 없습니다"))
            
            elif selected_val == "purchase":
                cur2.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? AND amount < 0 ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                log_con = ui.Container(ui.TextDisplay("## 최근 구매 내역"), accent_color=0xffffff)
                if logs:
                    for l in logs:
                        log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                        log_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 금액: {abs(l[0]):,}원 ({l[2].replace('제품구매(', '').replace(')', '')})\n<:dot_white:1482000567562928271> 시간: {l[1]}"))
                else:
                    log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    log_con.add_item(ui.TextDisplay("구매 내역이 없습니다"))
                
            await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
            
        selecao.callback = resp_callback
        container.add_item(ui.ActionRow(selecao))
        
        await it.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)

    async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cur.fetchall()]; conn.close()
        if not categories:
            return await it.response.send_message("**현재 등록된 제품 카테고리가 없습니다**", ephemeral=True)
        cat_con = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("원하시는 제품의 카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=options)
        async def cat_callback(interaction: discord.Interaction):
            selected = cat_select.values[0]
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            if products:
                for p in products:
                    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    item_info = (f"<:dot_white:1482000567562928271> 제품: {p[0]}\n<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개")
                    res_con.add_item(ui.TextDisplay(item_info))
            else:
                res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                res_con.add_item(ui.TextDisplay("등록된 제품이 없습니다."))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))
        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)

    async def chage_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)

    async def buy_callback(self, it: discord.Interaction):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0") 
        cats = [row[0] for row in cur.fetchall()]; conn.close()
        if not cats:
            return await it.response.send_message("**현재 구매 가능한 제품이 없습니다**", ephemeral=True)
        cat_con = ui.Container(ui.TextDisplay(f"## 카테고리 선택하기"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("구매할 제품 카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_options = [discord.SelectOption(label=c, value=c) for c in cats]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=cat_options)
        async def cat_callback(it2: discord.Interaction):
            selected_cat = cat_select.values[0]
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ? AND stock > 0", (selected_cat,))
            prods = cur.fetchall(); conn.close()
            prod_con = ui.Container(ui.TextDisplay(f"## 제품 선택하기"), accent_color=0xffffff)
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_con.add_item(ui.TextDisplay("구매할 제품을 선택해주세요"))
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_options = [discord.SelectOption(label=f"{p[0]}", description=f"가격: {p[1]:,}원 ㅣ 재고: {p[2]}개 ㅣ 누적 판매: {p[3]}개", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]
            prod_select = ui.Select(placeholder="구매하실 제품을 선택하세요", options=prod_options)
            async def prod_callback(it3: discord.Interaction):
                v = prod_select.values[0].split('|')
                await it3.response.send_modal(PurchaseModal(v[0], int(v[1]), int(v[2])))
            prod_select.callback = prod_callback
            prod_con.add_item(ui.ActionRow(prod_select))
            await it2.response.edit_message(view=ui.LayoutView().add_item(prod_con))
        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"DONE SYNC COMMANDS - Logged in as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="자판기", description="자판기 컨테이너를 전송합니다")
async def vending(interaction: discord.Interaction):
    await interaction.response.send_message("**자판기가 전송되었습니다**", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())

@bot.tree.command(name="기본설정", description="입금 계좌 정보/자충 여부")
async def set_account(interaction: discord.Interaction):
    await interaction.response.send_modal(AccountSetupModal())

@bot.tree.command(name="잔액관리", description="유저의 잔액을 추가/차감")
@discord.app_commands.describe(유저="잔액을 관리할 유저", 금액="설정할 금액", 여부="추가 또는 차감 선택")
@discord.app_commands.choices(여부=[
    discord.app_commands.Choice(name="추가", value="추가"),
    discord.app_commands.Choice(name="차감", value="차감")
])
async def balance_manage(interaction: discord.Interaction, 유저: discord.Member, 금액: int, 여부: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    
    if 여부 == "추가":
        cur.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 추가"
    else:
        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (금액, u_id))
        method_text = "관리자 차감"

    cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                (u_id, 금액 if 여부 == "추가" else -금액, time.strftime('%Y-%m-%d %H:%M'), method_text))
    
    conn.commit()
    conn.close()

    embed_color = 0x00ff00 if 여부 == "추가" else 0xff0000
    container = ui.Container(ui.TextDisplay(f"## 잔액 {여부} 완료"), accent_color=embed_color)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n금액: {금액:,}원\n잔액이 정상적으로 {여부}되었습니다"))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))

    try:
        dm_con = ui.Container(ui.TextDisplay(f"## 잔액 {여부} 안내"), accent_color=embed_color)
        dm_con.add_item(ui.TextDisplay(f"관리자에 의해 잔액이 **{금액:,}원** {여부}되었습니다."))
        await 유저.send(view=ui.LayoutView().add_item(dm_con))
    except:
        pass

@bot.tree.command(name="블랙리스트", description="유저를 블랙리스트에 추가/해제")
@discord.app_commands.describe(유저="블랙 관리할 유저", 여부="차단 또는 해제 선택")
@discord.app_commands.choices(여부=[
    discord.app_commands.Choice(name="차단", value=1),
    discord.app_commands.Choice(name="해제", value=0)
])
async def black_manage(interaction: discord.Interaction, 유저: discord.Member, 여부: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()
    
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    cur.execute("UPDATE users SET is_blacked = ? WHERE user_id = ?", (여부, u_id))
    
    conn.commit()
    conn.close()

    status_text = "차단" if 여부 == 1 else "해제"
    color = 0xff0000 if 여부 == 1 else 0x00ff00
    
    container = ui.Container(ui.TextDisplay(f"## 블랙리스트 {status_text}"), accent_color=color)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"대상: {유저.mention}\n해당 유저가 블랙리스트에서 {status_text}되었습니다"))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container))

@bot.tree.command(name="유저정보", description="유저의 상세 정보와 거래 내역을 조회합니다")
@app_commands.describe(유저="정보를 조회할 유저", 파일="텍스트 파일로 내보내기 여부")
@app_commands.choices(파일=[
    app_commands.Choice(name="파일로 받기", value="yes"),
    app_commands.Choice(name="파일 받지 않기", value="no")
])
async def user_info_manage(interaction: discord.Interaction, 유저: discord.Member, 파일: str = "no"):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()

    cur.execute("SELECT money, total_spent, is_blacked FROM users WHERE user_id = ?", (u_id,))
    user_row = cur.fetchone()
    
    cur.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 10", (u_id,))
    logs = cur.fetchall()
    conn.close()

    if not user_row:
        return await interaction.response.send_message("해당 유저의 데이터가 존재하지 않습니다.", ephemeral=True)

    money, total_spent, is_blacked = user_row
    black_status = "O" if is_blacked == 1 else "X"

    if 파일 == "yes":
        report_text = f"=== 유저 정보 보고서 ===\n"
        report_text += f"대상 유저: {유저.display_name} ({유저.id})\n"
        report_text += f"보유 잔액: {money:,}원\n"
        report_text += f"누적 충전: {total_spent:,}원\n"
        report_text += f"블랙 여부: {black_status}\n\n"
        report_text += "--- 최근 거래 내역 (최대 10개) ---\n"
        
        if logs:
            for l in logs:
                report_text += f"[{l[1]}] {l[2]}: {l[0]:,}원\n"
        else:
            report_text += "거래 내역이 없습니다.\n"

        file = discord.File(io.BytesIO(report_text.encode('utf-8')), filename=f"user_info_{u_id}.txt")
        return await interaction.response.send_message(f"```{유저.display_name}님의 상세 정보 파일입니다```", file=file, ephemeral=True)

    container = ui.Container(ui.TextDisplay(f"## {유저.display_name}님의 정보"), accent_color=0xffffff)
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"보유 잔액: {money:,}원\n누적 충전: {total_spent:,}원\n블랙 여부: {black_status}"))
    container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    select_options = [
        discord.SelectOption(label="최근 거래 내역 확인", value="view_logs")
    ]
    
    select_menu = ui.Select(placeholder="확인할 항목을 선택하세요", options=select_options)

    async def select_callback(it: discord.Interaction):
        if select_menu.values[0] == "view_logs":
            log_con = ui.Container(ui.TextDisplay(f"## {유저.display_name}님의 최근 내역"), accent_color=0xffffff)
            log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            if logs:
                log_text = "\n".join([f"• {l[1]} | {l[2]} | {l[0]:,}원" for l in logs])
                log_con.add_item(ui.TextDisplay(log_text))
            else:
                log_con.add_item(ui.TextDisplay("거래 내역이 존재하지 않습니다"))
            
            await it.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)

    select_menu.callback = select_callback
    container.add_item(ui.ActionRow(select_menu))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)

@bot.tree.command(name="상품설정", description="자판기 상품 정보를 관리합니다")
async def product_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("권한이 없습니다", ephemeral=True)
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)

@bot.tree.command(name="업데이트_공지", description="설정된 웹훅으로 컨테이너 공지를 전송합니다")
@app_commands.describe(내용="공지할 내용을 입력하세요")
async def update_notice_container(it: discord.Interaction, 내용: str):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("**관리자 권한이 필요합니다**", ephemeral=True)

    target_url = WEBHOOK_CONFIG.get("업데이트")
    if not target_url or "http" not in target_url:
        return await it.response.send_message("**웹훅 URL이 설정되지 않았습니다**", ephemeral=True)

    await it.response.defer(ephemeral=True)

    notice_con = ui.Container(ui.TextDisplay("## 업데이트 안내"), accent_color=0xffffff)
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    processed_content = 내용.replace("\\n", "\n")
    notice_con.add_item(ui.TextDisplay(f"{processed_content}"))
    
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    notice_con.add_item(ui.TextDisplay(f"`마지막 업데이트 시간: {time.strftime('%Y-%m-%d %H:%M')}`"))

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(target_url, session=session)
        try:
            view = ui.LayoutView().add_item(notice_con)
            
            await webhook.send(
                view=view,
                username="Service Update",
                avatar_url=bot.user.avatar.url if bot.user.avatar else None
            )
            await it.followup.send("**공지가 웹훅으로 전송되었습니다**", ephemeral=True)
        except Exception as e:
            await it.followup.send(f"**전송 실패: {e}**", ephemeral=True)

def run_web():
    uvicorn.run(app, host="127.0.0.1", port=8080)

if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    web_p = multiprocessing.Process(target=run_web)
    web_p.start()

    bot.run("")
