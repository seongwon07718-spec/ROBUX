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

# --- [ 문화상품권 충전 로직 ] ---
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

# --- [ 구매 시스템 (수정 포인트) ] ---
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
            err_con = ui.Container(ui.TextDisplay("## ❌ 입력 오류"), accent_color=0xff0000)
            err_con.add_item(ui.TextDisplay("숫자로만 입력해주세요."))
            return await it.response.send_message(view=ui.LayoutView().add_item(err_con), ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        # 구매 중 안내
        wait_con = ui.Container(ui.TextDisplay("## 🛒 구매 처리 중"), accent_color=0xffff00)
        wait_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        wait_con.add_item(ui.TextDisplay(f"**{self.prod_name}** {buy_count}개 결제를 진행 중입니다..."))
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)

        await asyncio.sleep(1) # 처리 연출

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        user_money = row[0] if row else 0

        res_con = ui.Container()
        if buy_count > self.stock:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## ❌ 재고 부족"))
            res_con.add_item(ui.TextDisplay(f"현재 남은 재고가 부족합니다. (재고: {self.stock}개)"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        
        if user_money < total_price:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## ❌ 잔액 부족"))
            res_con.add_item(ui.TextDisplay(f"필요: {total_price:,}원 / 보유: {user_money:,}원"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (buy_count, self.prod_name))
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, -total_price, time.strftime('%Y-%m-%d %H:%M'), f"제품구매({self.prod_name} x {buy_count})"))
        conn.commit(); conn.close()

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay("## 🎉 구매 완료"))
        res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        res_con.add_item(ui.TextDisplay(f"제품: **{self.prod_name}**\n수량: **{buy_count}개**\n차감: **{total_price:,}원**\n\nDM으로 영수증이 발송되었습니다."))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        try:
            dm_con = ui.Container(ui.TextDisplay(f"## 📦 구매 영수증"), accent_color=0x00ff00)
            dm_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            dm_con.add_item(ui.TextDisplay(f"제품: {self.prod_name}\n수량: {buy_count}개\n금액: {total_price:,}원\n날짜: {time.strftime('%Y-%m-%d %H:%M:%S')}"))
            await it.user.send(view=ui.LayoutView().add_item(dm_con))
        except: pass

# --- [ 관리자 및 기존 기능 (유지) ] ---
class ProductModal(ui.Modal, title="카테고리 / 제품 설정"):
    cat = ui.TextInput(label="카테고리"); name = ui.TextInput(label="제품명"); price = ui.TextInput(label="가격")
    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit(): return await it.response.send_message("숫자만 입력", ephemeral=True)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO products (category, name, price, stock) VALUES (?, ?, ?, COALESCE((SELECT stock FROM products WHERE name = ?), 0))", (self.cat.value, self.name.value, int(self.price.value), self.name.value))
        conn.commit(); conn.close(); await it.response.send_message("✅", ephemeral=True)

class StockModal(ui.Modal, title="재고 수량 관리"):
    name = ui.TextInput(label="제품명"); count = ui.TextInput(label="변경할 재고 수량")
    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit(): return await it.response.send_message("숫자만 입력", ephemeral=True)
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (int(self.count.value), self.name.value))
        if cur.rowcount == 0: conn.close(); return await it.response.send_message("제품 없음", ephemeral=True)
        conn.commit(); conn.close(); await it.response.send_message("✅", ephemeral=True)

class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 상품 관리 도구"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.select = ui.Select(placeholder="설정 항목 선택", options=[discord.SelectOption(label="제품 설정", value="prod"), discord.SelectOption(label="재고 설정", value="stock")])
        self.select.callback = self.admin_callback; self.container.add_item(ui.ActionRow(self.select)); self.add_item(self.container)
    async def admin_callback(self, it):
        if self.select.values[0] == "prod": await it.response.send_modal(ProductModal())
        else: await it.response.send_modal(StockModal())

class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(); self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green); approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red); cancel_btn.callback = self.cancel_callback
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn)); self.add_item(self.container)
    async def approve_callback(self, interaction):
        amt = int(self.amount); u_id = str(self.user.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amt, amt, u_id))
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", (u_id, amt, time.strftime('%Y-%m-%d %H:%M'), "수동(관리자)"))
        conn.commit(); conn.close(); database.update_status(self.db_id, "완료")
        self.container.clear_items(); self.container.accent_color = 0x00ff00; self.container.add_item(ui.TextDisplay(f"## 충전 승인 완료\n**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)
    async def cancel_callback(self, interaction):
        database.update_status(self.db_id, "취소"); self.container.clear_items(); self.container.accent_color = 0xff0000; self.container.add_item(ui.TextDisplay(f"## 충전 취소\n**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}"))
        await interaction.response.edit_message(view=self)

class AccountSetupModal(ui.Modal, title="계좌 정보 설정"):
    bank = ui.TextInput(label="은행명"); account = ui.TextInput(label="계좌번호"); owner = ui.TextInput(label="예금주")
    async def on_submit(self, interaction: discord.Interaction):
        global AUTO_LOG_ENABLED; BANK_CONFIG["bank_name"] = self.bank.value; BANK_CONFIG["account_num"] = self.account.value; BANK_CONFIG["owner"] = self.owner.value
        setup_con = ui.Container(ui.TextDisplay("## 계좌 설정 완료"), accent_color=0x00ff00)
        setup_con.add_item(ui.TextDisplay(f"은행: {self.bank.value}\n계좌: {self.account.value}\n예금주: {self.owner.value}"))
        if "카카오뱅크" in self.bank.value or "카뱅" in self.bank.value:
            btn1 = ui.Button(label="자동충전 허용", style=discord.ButtonStyle.green); btn2 = ui.Button(label="자동충전 거부", style=discord.ButtonStyle.red)
            async def cb1(it): global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = False; await it.response.send_message("허용됨", ephemeral=True)
            async def cb2(it): global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = True; await it.response.send_message("거부됨", ephemeral=True)
            btn1.callback = cb1; btn2.callback = cb2; setup_con.add_item(ui.ActionRow(btn1, btn2))
        await interaction.response.send_message(view=ui.LayoutView().add_item(setup_con), ephemeral=True)

class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__(); self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.TextDisplay(f"은행: {BANK_CONFIG['bank_name']}\n계좌: {BANK_CONFIG['account_num']}\n예주: {BANK_CONFIG['owner']}"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"입금자: {self.name}\n금액: {self.amount}원\n-# 5분 이내 입금 필요"))
        self.add_item(self.container)

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명"); amount = ui.TextInput(label="충전금액")
    async def on_submit(self, it: discord.Interaction):
        db_id = database.insert_request(it.user.id, self.amount.value); layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await it.response.send_message(view=layout, ephemeral=True)
        if AUTO_LOG_ENABLED:
            chan = bot.get_channel(LOG_CHANNEL_ID)
            if chan: await chan.send(view=AdminLogView(it.user, self.name.value, self.amount.value, db_id))
        key = f"{self.name.value}_{self.amount.value}"
        asyncio.create_task(self.watch_deposit(it, layout, key, self.amount.value))
    async def watch_deposit(self, it, layout, key, amount):
        start = time.time()
        while time.time() - start < 300:
            await asyncio.sleep(3)
            if pending_deposits.get(key):
                amt = int(amount); u_id = str(it.user.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
                cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amt, amt, u_id))
                cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", (u_id, amt, time.strftime('%Y-%m-%d %H:%M'), "자동(계좌)"))
                conn.commit(); conn.close(); del pending_deposits[key]; database.update_status(layout.db_id, "완료")
                layout.container.clear_items(); layout.container.accent_color = 0x00ff00; layout.container.add_item(ui.TextDisplay("## 자동충전 완료\n금액: " + amount + "원"))
                try: await it.edit_original_response(view=layout)
                except: pass
                return
        database.update_status(layout.db_id, "시간초과"); layout.container.clear_items(); layout.container.accent_color = 0xff0000; layout.container.add_item(ui.TextDisplay("## 시간 초과")); await it.edit_original_response(view=layout)

class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        con = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        b1 = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray); b1.callback = self.bank_callback
        b2 = ui.Button(label="문상결제", style=discord.ButtonStyle.gray); b2.callback = self.gift_card_callback
        con.add_item(ui.ActionRow(b1, b2)); self.add_item(con)
    async def bank_callback(self, it): await it.response.send_modal(BankModal())
    async def gift_card_callback(self, it): await it.response.send_modal(CultureModal(bot, LOG_CHANNEL_ID))

class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 테스트"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        buy = ui.Button(label="구매", emoji="<:emoji_26:1480171245415694336>")
        shop = ui.Button(label="제품", emoji="<:emoji_29:1480171320804118708>")
        chage = ui.Button(label="충전", emoji="<:emoji_28:1480171287752999043>")
        info = ui.Button(label="정보", emoji="<:emoji_27:1480171268333506622>")
        shop.callback = self.shop_callback; chage.callback = self.chage_callback; buy.callback = self.buy_callback; info.callback = self.info_callback
        self.container.add_item(ui.ActionRow(buy, shop, chage, info)); self.add_item(self.container)
    
    async def shop_callback(self, it):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT DISTINCT category FROM products"); cats = [row[0] for row in cur.fetchall()]; conn.close()
        if not cats: return await it.response.send_message("카테고리 없음", ephemeral=True)
        cat_con = ui.Container(ui.TextDisplay("## 카테고리 선택"), accent_color=0xffffff)
        opts = [discord.SelectOption(label=cat, value=cat) for cat in cats]; sel = ui.Select(placeholder="선택", options=opts)
        async def cat_cb(interaction):
            s = sel.values[0]; conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT name, price, stock FROM products WHERE category = ?", (s,)); prods = cur.fetchall(); conn.close()
            txt = "\n".join([f"• {p[0]} - {p[1]:,}원 (재고: {p[2]}개)" for p in prods])
            res = ui.Container(ui.TextDisplay(f"## {s} 제품 목록"), accent_color=0xffffff); res.add_item(ui.TextDisplay(txt)); res.add_item(ui.ActionRow(sel))
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res))
        sel.callback = cat_cb; cat_con.add_item(ui.ActionRow(sel)); await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
    
    async def chage_callback(self, it):
        if await check_black(it): return
        await it.response.send_message(view=ChargeLayout(), ephemeral=True)
    
    async def buy_callback(self, it):
        if await check_black(it): return
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT DISTINCT category FROM products WHERE stock > 0"); cats = [row[0] for row in cur.fetchall()]; conn.close()
        if not cats: return await it.response.send_message("구매 가능 제품 없음", ephemeral=True)
        cat_con = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        cat_opts = [discord.SelectOption(label=c, value=c) for c in cats]; cat_sel = ui.Select(placeholder="카테고리 선택", options=cat_opts)
        async def cat_cb(it2):
            s_cat = cat_sel.values[0]; conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT name, price, stock FROM products WHERE category = ? AND stock > 0", (s_cat,)); prods = cur.fetchall(); conn.close()
            p_con = ui.Container(ui.TextDisplay("## 제품 선택"), accent_color=0xffffff)
            p_opts = [discord.SelectOption(label=f"{p[0]}ㅣ{p[1]:,}원", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]; p_sel = ui.Select(placeholder="제품 선택", options=p_opts)
            async def p_cb(it3): n, p, s = p_sel.values[0].split('|'); await it3.response.send_modal(PurchaseModal(n, int(p), int(s)))
            p_sel.callback = p_cb; p_con.add_item(ui.ActionRow(p_sel)); await it2.response.edit_message(view=ui.LayoutView().add_item(p_con))
        cat_sel.callback = cat_cb; cat_con.add_item(ui.ActionRow(cat_sel)); await it.response.send_message(view=ui.LayoutView().add_item(cat_con), ephemeral=True)
    
    async def info_callback(self, it):
        if await check_black(it): return
        await it.response.defer(ephemeral=True); u_id = str(it.user.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,)); row = cur.fetchone(); conn.close()
        m, s = (row[0], row[1]) if row else (0, 0)
        con = ui.Container(ui.TextDisplay(f"## {it.user.display_name}님 정보"), accent_color=0xffffff); con.add_item(ui.TextDisplay(f"잔액: {m:,}원\n누적: {s:,}원"))
        sel = ui.Select(placeholder="내역 조회", options=[discord.SelectOption(label="충전 내역", value="c"), discord.SelectOption(label="구매 내역", value="p")])
        async def cb(i):
            conn2 = sqlite3.connect('vending_data.db'); cur2 = conn2.cursor(); cur2.execute("SELECT amount, date FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 5", (u_id,)); logs = cur2.fetchall(); conn2.close()
            l_con = ui.Container(ui.TextDisplay("## 내역"), accent_color=0xffffff); l_con.add_item(ui.TextDisplay("\n".join([f"• {l[1]} | {l[0]:,}원" for l in logs]) if logs else "내역 없음")); await i.response.send_message(view=ui.LayoutView().add_item(l_con), ephemeral=True)
        sel.callback = cb; con.add_item(ui.ActionRow(sel)); await it.followup.send(view=ui.LayoutView().add_item(con), ephemeral=True)

# --- [ 봇 명령어 (기능 무수정 그대로 유지) ] ---
@bot.event
async def on_ready(): await bot.tree.sync(); print(f"✅ {bot.user} 로그인")

@bot.tree.command(name="자판기", description="자판기 호출")
async def vending(it): await it.response.send_message("자판기 전송됨", ephemeral=True); await it.channel.send(view=MeuLayout())

@bot.tree.command(name="기본설정", description="계좌 설정")
async def set_acc(it): await it.response.send_modal(AccountSetupModal())

@bot.tree.command(name="잔액관리", description="유저 잔액 조절")
async def bal_man(it, 유저: discord.Member, 금액: int, 여부: str):
    if not it.user.guild_permissions.administrator: return await it.response.send_message("권한 없음", ephemeral=True)
    u_id = str(유저.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    if 여부 == "추가": cur.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (금액, u_id))
    else: cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (금액, u_id))
    cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", (u_id, 금액 if 여부=="추가" else -금액, time.strftime('%Y-%m-%d %H:%M'), "관리자 조절"))
    conn.commit(); conn.close(); con = ui.Container(ui.TextDisplay(f"## 잔액 {여부} 완료"), accent_color=0x00ff00); con.add_item(ui.TextDisplay(f"대상: {유저.mention}\n금액: {금액:,}원")); await it.response.send_message(view=ui.LayoutView().add_item(con))

@bot.tree.command(name="블랙리스트", description="유저 차단")
async def black_man(it, 유저: discord.Member, 여부: int):
    if not it.user.guild_permissions.administrator: return await it.response.send_message("권한 없음", ephemeral=True)
    u_id = str(유저.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
    cur.execute("UPDATE users SET is_blacked = ? WHERE user_id = ?", (여부, u_id)); conn.commit(); conn.close()
    await it.response.send_message(f"{유저.mention} 블랙리스트 상태 변경: {여부}")

@bot.tree.command(name="유저정보", description="유저 상세 조회")
async def user_info_man(it, 유저: discord.Member, 파일: str = "no"):
    if not it.user.guild_permissions.administrator: return await it.response.send_message("권한 없음", ephemeral=True)
    u_id = str(유저.id); conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT money, total_spent, is_blacked FROM users WHERE user_id = ?", (u_id,)); row = cur.fetchone(); conn.close()
    if not row: return await it.response.send_message("정보 없음", ephemeral=True)
    con = ui.Container(ui.TextDisplay(f"## {유저.display_name} 정보"), accent_color=0xffffff); con.add_item(ui.TextDisplay(f"잔액: {row[0]:,}원\n누적: {row[1]:,}원\n블랙: {'O' if row[2]==1 else 'X'}")); await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

@bot.tree.command(name="상품설정", description="상품 관리")
async def prod_set(it):
    if not it.user.guild_permissions.administrator: return await it.response.send_message("권한 없음", ephemeral=True)
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)

async def check_black(it):
    conn = sqlite3.connect('vending_data.db'); cur = conn.cursor(); cur.execute("SELECT is_blacked FROM users WHERE user_id = ?", (str(it.user.id),)); row = cur.fetchone(); conn.close()
    if row and row[0] == 1: return True
    return False

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run("TOKEN")
