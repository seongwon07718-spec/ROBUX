import discord
import asyncio
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
from fastapi import FastAPI, Request 
from pydantic import BaseModel  
from threading import Thread 

app = FastAPI()

class ChargeData(BaseModel):
    message: str

pending_deposits = {}

@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    print(f"📥 [입금 문자 수신]:\n{msg}")
    
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

BANK_CONFIG = {
    "bank_name": "카카오뱅크",
    "account_num": "7777-03-6763823",
    "owner": "정성원"
}
AUTO_LOG_ENABLED = True

LOG_CHANNEL_ID = 1477980009753739325
CULTURE_COOKIE = "JSESSIONID=e6901716-3acc-4989-8477-f42b90668333; KeepLoginConfig=DD8nG9NnsjZkfQwNNwUZbd7V563XXjGNw6sATI2UGlUkJVfG%2Bq7l62X%2BIdGFRH6Q; LoginConfig=UserID%3Djmk0908076%26SavedID%3DY; baseInfo=baseTypeA=Odg+gykSm8l9qLRKwZrNPUn8VfLBy5ErrPk2qgkRr9UDR275mKa4rzS+zB2ul524fZTCk78evSB7zzTdiIJvhQ==&baseTypeB=Odg+gykSm8l9qLRKwZrNPaj0Hdr4KaBR9VCDYJVnUX80tkb65kKFC6x6H5f4KAbkn3ExDQalsLUJWUg09FsH1fGij3yos7xohMIzHo+eIq86YdqoESUmSVjDbDKdsWQ4hYFWoqF6NfyUABwO6Hgr+IrW2cr0hGIM4oUXxniHqiZ79eX9GPYlfiOCJMCT1fJi434PCXG6UvDfPveBNZYn8g==&baseTypeC=Odg+gykSm8l9qLRKwZrNPb6tfv9jKjJFOPZXi05gP0lw4yYV2/CZWy7TGe6tQejK"

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

class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name = prod_name
        self.price = price
        self.stock = stock
        self.count = ui.TextInput(label="구매 수량", placeholder=f"수량을 입력하세요ㅣ재고: {stock}개", min_length=1, max_length=5)
        self.add_item(self.count)

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("❌ 숫자로만 입력해주세요.", ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()

        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        user_money = cur.fetchone()
        user_money = user_money[0] if user_money else 0

        if buy_count > self.stock:
            return await it.response.send_message(f"❌ 재고가 부족합니다. (현재 재고: {self.stock}개)", ephemeral=True)
        
        if user_money < total_price:
            return await it.response.send_message(f"❌ 잔액이 부족합니다. (필요 금액: {total_price:,}원 / 보유: {user_money:,}원)", ephemeral=True)

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (buy_count, self.prod_name))
        
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        
        conn.commit()
        conn.close()

        res_con = ui.Container(ui.TextDisplay(f"## 🎉 구매 완료"), accent_color=0x00ff00)
        res_con.add_item(ui.TextDisplay(f"제품명: **{self.prod_name}**\n구매 수량: **{buy_count}개**\n차감 금액: **{total_price:,}원**\n\n구매가 성공적으로 완료되었습니다!"))
        
        await it.response.send_message(view=ui.LayoutView().add_item(res_con), ephemeral=True)

class ProductModal(ui.Modal, title="카테고리 / 제품 설정"):
    cat = ui.TextInput(label="카테고리")
    name = ui.TextInput(label="제품명")
    price = ui.TextInput(label="가격")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("가격은 숫자만 입력해주세요", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO products (category, name, price, stock) VALUES (?, ?, ?, COALESCE((SELECT stock FROM products WHERE name = ?), 0))", 
                    (self.cat.value, self.name.value, int(self.price.value), self.name.value))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅", ephemeral=True)

class StockModal(ui.Modal, title="재고 수량 관리"):
    name = ui.TextInput(label="제품명")
    count = ui.TextInput(label="변경할 재고 수량")

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("재고 수량은 숫자만 입력해주세요", ephemeral=True)

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (int(self.count.value), self.name.value))
        if cur.rowcount == 0:
            conn.close()
            return await it.response.send_message("해당 이름의 제품을 찾을 수 없습니다", ephemeral=True)
        conn.commit(); conn.close()
        await it.response.send_message(f"✅", ephemeral=True)

class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리 도구"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("카테고리 / 제품 / 재고 설정해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.select = ui.Select(placeholder="설정할 항목을 선택하세요", options=[
            discord.SelectOption(label="카테고리 / 제품 설정", value="prod"),
            discord.SelectOption(label="재고 설정", value="stock")
        ])
        self.select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        if self.select.values[0] == "prod": await it.response.send_modal(ProductModal())
        else: await it.response.send_modal(StockModal())

class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(); self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green); approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red); cancel_btn.callback = self.cancel_callback
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
        self.container.add_item(ui.TextDisplay(f"## 충전 완료 (수동 승인)"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        
        await interaction.response.edit_message(view=self)
        
        try: 
            await self.user.send(f"**{self.amount}원 충전이 완료되었습니다 (관리자 승인)**")
        except: 
            pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
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
        super().__init__(); self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"은행명: {BANK_CONFIG['bank_name']}\n계좌: {BANK_CONFIG['account_num']}\n예금주: {BANK_CONFIG['owner']}"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"입금자명: {self.name}\n충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 충전이 완료됩니다"))
        self.add_item(self.container)
    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)
        if database.get_status(self.db_id) == "대기":
            self.container.clear_items(); self.container.accent_color = 0xff0000
            self.container.add_item(ui.TextDisplay("## 충전 시간 초과")); self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.container.add_item(ui.TextDisplay("자동충전 시간이 초과되었습니다"))
            await interaction.edit_original_response(view=self)

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
                layout.container.add_item(ui.TextDisplay("5분 이내에 입금이 확인되지 않아 취소되었습니다."))
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
                layout.container.add_item(ui.TextDisplay("## 자동충전 완료"))
                layout.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                layout.container.add_item(ui.TextDisplay(f"충전금액: **{amount_int:,}원**\n성공적으로 충전이 완료되었습니다"))
                    
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small)); container.add_item(ui.TextDisplay("원하시는 충전 수단을 선택해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray); bank.callback = self.bank_callback
        gift_card = ui.Button(label="문상결제", style=discord.ButtonStyle.gray); gift_card.callback = self.gift_card_callback
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
        self.container = ui.Container(ui.TextDisplay("## 테스트"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        buy = ui.Button(label="구매", emoji="<:emoji_26:1480171245415694336>")
        shop = ui.Button(label="제품", emoji="<:emoji_29:1480171320804118708>")
        chage = ui.Button(label="충전", emoji="<:emoji_28:1480171287752999043>")
        info = ui.Button(label="정보", emoji="<:emoji_27:1480171268333506622>")
        shop.callback = self.shop_callback
        chage.callback = self.chage_callback
        buy.callback = self.buy_callback
        info.callback = self.info_callback
        self.container.add_item(ui.ActionRow(buy, shop, chage, info))
        self.add_item(self.container)
    async def shop_callback(self, it: discord.Interaction):
        if await check_black(it): return
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cur.fetchall()]
        conn.close()

        if not categories:
            return await it.response.send_message("현재 등록된 제품 카테고리가 없습니다.", ephemeral=True)

        cat_con = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("원하시는 제품의 카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        options = [discord.SelectOption(label=cat, value=cat) for cat in categories]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=options)

        async def cat_callback(interaction: discord.Interaction):
            selected = cat_select.values[0]
            
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()

            item_text = "\n".join([f"• {p[0]} - {p[1]:,}원 (재고: {p[2]}개)" for p in products]) if products else "제품이 없습니다."
            
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"{item_text}"))
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

        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0") 
        cats = [row[0] for row in cur.fetchall()]
        conn.close()

        if not cats:
            return await it.response.send_message("❌ 현재 구매 가능한 제품이 없습니다.", ephemeral=True)

        cat_con = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_con.add_item(ui.TextDisplay("카테고리를 선택해주세요"))
        cat_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        cat_options = [discord.SelectOption(label=c, value=c) for c in cats]
        cat_select = ui.Select(placeholder="카테고리를 선택하세요", options=cat_options)

        async def cat_callback(it2: discord.Interaction):
            selected_cat = cat_select.values[0]
            
            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock FROM products WHERE category = ? AND stock > 0", (selected_cat,))
            prods = cur.fetchall(); conn.close()

            prod_con = ui.Container(ui.TextDisplay(f"## 구매하기"), accent_color=0xffffff)
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_con.add_item(ui.TextDisplay("구매할 제품을 선택해주세요"))
            prod_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            prod_options = [discord.SelectOption(label=f"{p[0]}ㅣ{p[1]:,}원", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]
            prod_select = ui.Select(placeholder="구매하실 제품을 선택하세요", options=prod_options)

            async def prod_callback(it3: discord.Interaction):
                p_name, p_price, p_stock = prod_select.values[0].split('|')
                await it3.response.send_modal(PurchaseModal(p_name, int(p_price), int(p_stock)))

            prod_select.callback = prod_callback
            prod_con.add_item(ui.ActionRow(prod_select))
            await it2.response.edit_message(view=ui.LayoutView().add_item(prod_con))

        cat_select.callback = cat_callback
        cat_con.add_item(ui.ActionRow(cat_select))
        await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
    async def info_callback(self, it: discord.Interaction):
        if await check_black(it): return
        await it.response.defer(ephemeral=True)
        u_id = str(it.user.id)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); conn.close()
        money, total_spent = (row[0], row[1]) if row else (0, 0)
        container = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"보유 잔액: {money:,}원\n누적 금액: {total_spent:,}원"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="<:emoji_28:1480171287752999043>"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="<:emoji_26:1480171245415694336>")
        ])
        async def resp(i: discord.Interaction):
            if selecao.values[0] == "charge":
                conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor()
                cur2.execute("SELECT amount, date FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 5", (u_id,))
                logs = cur2.fetchall(); conn2.close()
                
                log_con = ui.Container(ui.TextDisplay("## 최근 충전 내역"), accent_color=0xffffff)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                if logs:
                    log_text = "\n".join([f"• {l[1]} | {l[0]:,}원" for l in logs])
                    log_con.add_item(ui.TextDisplay(log_text))
                else: log_con.add_item(ui.TextDisplay("내역이 없습니다"))
                await i.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)
        selecao.callback = resp
        container.add_item(ui.ActionRow(selecao))
        await it.followup.send(view=ui.LayoutView().add_item(container), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("-" * 40)
    print(f"자판기 봇 로그인: {bot.user}")
    print(f"iOS 자동충전 시스템: 통합 가동 중 (Port: 88)")
    print(f"접속 주소: https://pay.rbxshop.cloud")
    print("-" * 40)

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
        await 유저.send(f"**잔액이 {금액:,}원 {여부}되었습니다**")
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

if __name__ == "__main__":
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()
