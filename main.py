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
import ios_charge

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1477980009753739325
CULTURE_COOKIE = "JSESSIONID=e6901716-3acc-4989-8477-f42b90668333; KeepLoginConfig=DD8nG9NnsjZkfQwNNwUZbd7V563XXjGNw6sATI2UGlUkJVfG%2Bq7l62X%2BIdGFRH6Q; LoginConfig=UserID%3Djmk0908076%26SavedID%3DY; baseInfo=baseTypeA=Odg+gykSm8l9qLRKwZrNPUn8VfLBy5ErrPk2qgkRr9UDR275mKa4rzS+zB2ul524fZTCk78evSB7zzTdiIJvhQ==&baseTypeB=Odg+gykSm8l9qLRKwZrNPaj0Hdr4KaBR9VCDYJVnUX80tkb65kKFC6x6H5f4KAbkn3ExDQalsLUJWUg09FsH1fGij3yos7xohMIzHo+eIq86YdqoESUmSVjDbDKdsWQ4hYFWoqF6NfyUABwO6Hgr+IrW2cr0hGIM4oUXxniHqiZ79eX9GPYlfiOCJMCT1fJi434PCXG6UvDfPveBNZYn8g==&baseTypeC=Odg+gykSm8l9qLRKwZrNPb6tfv9jKjJFOPZXi05gP0lw4yYV2/CZWy7TGe6tQejK"

async def do_culture_charge(pin_string):
    """주신 코드 방식: Pin 객체 생성 -> 리스트 전달 -> 결과 객체 반환"""
    try:
        cl = culture_logic.Cultureland()
        await cl.login(CULTURE_COOKIE)

        target_pin = culture_logic.Pin(pin_string) 

        result_obj = await cl.charge_process([target_pin]) 

        await cl.close()

        final_res = result_obj[0] if isinstance(result_obj, list) else result_obj

        return {
            "status": "success" if final_res.amount > 0 else "error",
            "amount": final_res.amount,
            "message": final_res.message
        }

    except Exception as e:
        print(f"❌ [컬쳐랜드 에러]: {e}")
        return {"status": "error", "message": str(e)}

    
class CultureModal(ui.Modal, title="문상 정보"):
    pin = ui.TextInput(
        label="핀번호 입력", 
        placeholder="하이픈(-) 없이 숫자만 입력하세요",
        min_length=16,
        max_length=19
    )

    def __init__(self, bot, log_channel_id):
        super().__init__()
        self.bot = bot
        self.log_channel_id = log_channel_id

    async def on_submit(self, it: discord.Interaction):
        wait_con = ui.Container(ui.TextDisplay("## 핀번호 확인 중"), accent_color=0xffff00)
        wait_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        wait_con = ui.Container(
        ui.TextDisplay("## 핀번호 확인 중"),
        ui.TextDisplay("약 5~10초 정도 소요됩니다\n잠시만 기다려 주세요"),
        accent_color=0xffff00
     )
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)

        clean_pin = str(self.pin.value).replace("-", "").strip()

        res = await do_culture_charge(clean_pin)

        result_con = ui.Container()
        
        if res["status"] == "success" and res.get("amount", 0) > 0:
            amount = res["amount"]
            u_id = str(it.user.id)
            
            conn = sqlite3.connect('vending_data.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount, amount, u_id))
            conn.commit()
            conn.close()
            
            result_con.accent_color = 0x00ff00
            result_con.add_item(ui.TextDisplay(f"## 충전 성공"))
            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            result_con.add_item(ui.TextDisplay(f"**충전 금액:** {amount:,}원\n잔액이 정상적으로 반영되었습니다"))
            
            log_chan = self.bot.get_channel(self.log_channel_id)
            if log_chan is None:
                try: log_chan = await self.bot.fetch_channel(self.log_channel_id)
                except: pass

            if log_chan:
                log_con = ui.Container(ui.TextDisplay(f"## 문상 충전로그"), accent_color=0x00ff00)
                log_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                log_con.add_item(ui.TextDisplay(f"**신청자:** {it.user.mention}\n**충전금액:** {amount:,}원\n**상태:** 자동 승인 완료"))
                await log_chan.send(view=ui.LayoutView().add_item(log_con))
        else:
            reason = res.get("message", "잘못된 핀번호이거나 이미 사용된 번호입니다")
            result_con.accent_color = 0xff0000
            result_con.add_item(ui.TextDisplay(f"## 충전 실패"))
            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            result_con.add_item(ui.TextDisplay(f"**사유:** {reason}"))

        await it.edit_original_response(view=ui.LayoutView().add_item(result_con))

class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__()
        self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green)
        approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red)
        cancel_btn.callback = self.cancel_callback
        
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn))
        self.add_item(self.container)

    async def approve_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "완료")
        self.container.clear_items()
        self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)
        try: await self.user.send(f"**{self.amount}원 충전이 완료되었습니다**")
        except: pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)

class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.name = name
        self.amount = amount
        self.db_id = db_id

        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0x00ff00)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"은행명: 카카오뱅크\n계좌: 7777-03-6763823\n예금주: 정성원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(f"입금자명: {self.name}\n충전금액: {self.amount}원"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 충전이 완료됩니다"))
        self.add_item(self.container)

    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)
        if database.get_status(self.db_id) == "대기":
            self.container.clear_items()
            self.container.accent_color = 0xff0000
            self.container.add_item(ui.TextDisplay("## 충전 시간 초과"))
            self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
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

        last_time = database.get_last_request_time(interaction.user.id)
        current_time = time.time()
        if current_time - last_time < 300:
            remaining = int(300 - (current_time - last_time))
            return await interaction.response.send_message(f"**이전 신청 기록이 있습니다. {remaining}초 후 다시 시도해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        
        await interaction.response.send_message(view=layout, ephemeral=True)

        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        charge_msg = f"{self.name.value} {self.amount.value}"
        result = ios_charge.send_charge_message(charge_msg)

        if result.get("ok"):
            amount_int = int(self.amount.value)
            u_id = str(interaction.user.id)
            conn = sqlite3.connect('vending_data.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
            conn.commit()
            conn.close()

            await interaction.followup.send(f"✅ **입금이 확인되어 {amount_int:,}원이 자동 충전되었습니다!**", ephemeral=True)
        
        asyncio.create_task(layout.start_timer(interaction))

class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("원하시는 충전 수단을 선택해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
        bank.callback = self.bank_callback
        
        gift_card = ui.Button(label="문상결제", style=discord.ButtonStyle.gray)
        gift_card.callback = self.gift_card_callback
        
        button_row = ui.ActionRow(bank, gift_card)
        container.add_item(button_row)
        self.add_item(container)

    async def bank_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BankModal())

    async def gift_card_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CultureModal(bot, LOG_CHANNEL_ID))

class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 구매하기"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("테스트"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        shop = ui.Button(label="제품")
        shop.callback = self.shop_callback
        chage = ui.Button(label="충전")
        chage.callback = self.chage_callback
        buy = ui.Button(label="구매")
        buy.callback = self.buy_callback
        info = ui.Button(label="정보")
        info.callback = self.info_callback

        button = ui.ActionRow(shop, chage, buy, info)
        container.add_item(button)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("-# © 2026 Made by **@alx.io07** All rights reserved"))
        self.add_item(container)

    async def shop_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def chage_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ChargeLayout(), ephemeral=True)

    async def buy_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def info_callback(self, interaction: discord.Interaction):
        u_id = str(interaction.user.id)
        
        conn = sqlite3.connect('vending_data.db')
        cur = conn.cursor()
        cur.execute("SELECT money, total_spent FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone()
        conn.close()

        money, total_spent = (row[0], row[1]) if row else (0, 0)

        container = ui.Container(ui.TextDisplay(f"## {interaction.user.display_name}님의 정보"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"보유 잔액: ₩{money:,}\n누적 금액: ₩{total_spent:,}"))

        selecao = ui.Select(placeholder="거래 내역 조회하기", options=[
            discord.SelectOption(label="최근 구매 내역", value="buy", emoji="🛒"),
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="💳")
        ])

        async def resposta_selecao(it: discord.Interaction):
            escolha = selecao.values[0]
            if escolha == "buy":
                await it.response.send_message(f"**{it.user.name}**님, 구매 내역이 없습니다", ephemeral=True)
            else:
                await it.response.send_message(f"**{it.user.name}**님, 충전 내역이 없습니다", ephemeral=True)

        selecao.callback = resposta_selecao

        linha = ui.ActionRow()
        linha.add_item(selecao)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(linha)

        info_view = ui.LayoutView()
        info_view.add_item(container)

        await interaction.response.send_message(view=info_view, ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("-" * 40)
    print(f"자판기 봇 로그인: {bot.user}")
    print(f"iOS 자동충전 시스템: 정상 작동 중")
    print(f"외부 접속 주소: https://pay.rbxshop.cloud")
    print("-" * 40)

@bot.tree.command(name="자판기", description="자판기를 전송합니다")
async def vending(interaction: discord.Interaction):
    await interaction.response.send_message("**자판기가 전송되었습니다**", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())

if __name__ == "__main__":
