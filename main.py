import sqlite3
import discord
import asyncio
import time
import re
from discord import ui

# ==========================================
# [ SECTION 1: 블랙리스트 확인 로직 ]
# ==========================================
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

# ==========================================
# [ SECTION 2: 관리자 전용 기능 ]
# ==========================================

# 1. 충전 승인/취소 로그 뷰
class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__()
        self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 신청자: {user.mention}\n"
            f"<:dot_white:1482000567562928271> 입금자명: {name}\n"
            f"<:dot_white:1482000567562928271> 신청금액: {amount}원"
        ))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        approve_btn = ui.Button(label="완료", emoji="<:UpArrow:1482008374777483324>")
        approve_btn.callback = self.approve_callback
        
        cancel_btn = ui.Button(label="취소", emoji="<:DownArrow:1482008377482678335>")
        cancel_btn.callback = self.cancel_callback
        
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn))
        self.add_item(self.container)

    async def approve_callback(self, interaction: discord.Interaction):
        amount_int = int(self.amount)
        u_id = str(self.user.id)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
        cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                    (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "수동(관리자)"))
        conn.commit(); conn.close()

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
        except: pass

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

# 2. 계좌 정보 설정 모달
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
                global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = False
                await it.response.send_message("**자동충전이 허용되었습니다 (로그 미발송)**", ephemeral=True)
            
            async def deny_cb(it):
                global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = True
                await it.response.send_message("**자동충전이 거부되었습니다 (로그 발송)**", ephemeral=True)
            
            allow_btn.callback, deny_btn.callback = allow_cb, deny_cb
            setup_con.add_item(ui.ActionRow(allow_btn, deny_btn))
        
        view.add_item(setup_con)
        await interaction.response.send_message(view=view, ephemeral=True)

# ==========================================
# [ SECTION 3: 사용자 전용 기능 ]
# ==========================================

# 1. 충전 방식 선택 뷰
class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("원하시는 충전 수단을 선택해주세요"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray, emoji="<:dot_white:1482000567562928271>")
        bank.callback = self.bank_callback
        
        gift_card = ui.Button(label="문상결제", style=discord.ButtonStyle.gray, emoji="<:dot_white:1482000567562928271>")
        gift_card.callback = self.gift_card_callback
        
        container.add_item(ui.ActionRow(bank, gift_card))
        self.add_item(container)

    async def bank_callback(self, it): await it.response.send_modal(BankModal())
    async def gift_card_callback(self, it): await it.response.send_modal(CultureModal(bot, LOG_CHANNEL_ID))

# 2. 계좌 정보 표시 뷰
class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 은행명: {BANK_CONFIG['bank_name']}\n"
            f"<:dot_white:1482000567562928271> 계좌번호: {BANK_CONFIG['account_num']}\n"
            f"<:dot_white:1482000567562928271> 예금주: {BANK_CONFIG['owner']}\n"
            f"<:dot_white:1482000567562928271> 충전금액: {self.amount}원"
        ))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("-# 5분 이내로 입금해주셔야 자동충전됩니다"))
        
        self.copy_btn = ui.Button(label="계좌복사", style=discord.ButtonStyle.gray, emoji="<:copy:1482673389679415316>")
        self.copy_btn.callback = self.copy_callback
        self.container.add_item(ui.ActionRow(self.copy_btn))
        self.add_item(self.container)

    async def copy_callback(self, it: discord.Interaction):
        self.copy_btn.disabled = True
        await it.response.edit_message(view=self)
        await it.followup.send(content=f"{BANK_CONFIG['account_num']}", ephemeral=True)

# 3. 계좌이체 신청 모달 및 감시 로직
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

        name_val, amount_val = self.name.value, self.amount.value
        key = f"{name_val}_{amount_val}"
        asyncio.create_task(self.watch_deposit(interaction, layout, name_val, amount_val, key))

    async def watch_deposit(self, interaction, layout, name, amount, key):
        start_time = time.time()
        while True:
            if time.time() - start_time > 300: # 5분 초과 시
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "시간초과")
                layout.container.clear_items(); layout.container.accent_color = 0xff0000
                layout.container.add_item(ui.TextDisplay("## 입금 시간 초과"))
                layout.container.add_item(ui.TextDisplay("5분 이내에 입금이 확인되지 않아 취소되었습니다"))
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

            await asyncio.sleep(3)
            if pending_deposits.get(key):
                amount_int = int(amount); u_id = str(interaction.user.id)
                conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
                cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount_int, amount_int, u_id))
                cur.execute("INSERT INTO charge_logs (user_id, amount, date, method) VALUES (?, ?, ?, ?)", 
                            (u_id, amount_int, time.strftime('%Y-%m-%d %H:%M'), "자동(계좌)"))
                conn.commit(); conn.close()
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "완료")

                layout.container.clear_items(); layout.container.accent_color = 0x00ff00
                layout.container.add_item(ui.TextDisplay("## 충전 완료"))
                layout.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 충전금액: {amount_int:,}원"))
                layout.container.add_item(ui.TextDisplay("-# 성공적으로 충전이 완료되었습니다"))
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break
