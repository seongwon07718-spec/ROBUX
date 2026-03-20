import sqlite3
import discord
import asyncio
import time
import re
from discord import ui

# --- [1] 관리자용: 충전 승인/취소 뷰 ---
class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__(timeout=None)
        self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 충전 신청"), accent_color=0xffffff)
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay(
            f"<:dot_white:1482000567562928271> 신청자: {user.mention}\n"
            f"<:dot_white:1482000567562928271> 입금자명: {name}\n"
            f"<:dot_white:1482000567562928271> 신청금액: {amount}원"
        ))
        
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
        
        # 관리자 메시지 업데이트
        self.container.clear_items()
        self.container.accent_color = 0x00ff00
        self.container.add_item(ui.TextDisplay(f"## 충전 완료"))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 처리자: {interaction.user.mention}\n<:dot_white:1482000567562928271> 대상: {self.user.mention}\n<:dot_white:1482000567562928271> 금액: {self.amount}원"))
        await interaction.response.edit_message(view=self)
        
        # 사용자 DM 전송
        try: 
            dm_con = ui.Container(ui.TextDisplay("## 충전 완료"), accent_color=0x00ff00)
            dm_con.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> {self.amount}원 충전이 완료되었습니다"))
            await self.user.send(view=ui.LayoutView().add_item(dm_con))
        except: pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.accent_color = 0xff0000
        self.container.add_item(ui.TextDisplay(f"## 충전 취소"))
        self.container.add_item(ui.TextDisplay(f"<:dot_white:1482000567562928271> 처리자: {interaction.user.mention}\n<:dot_white:1482000567562928271> 대상: {self.user.mention}"))
        await interaction.response.edit_message(view=self)

# --- [2] 사용자용: 충전 신청 및 정보 조회 ---
class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"), accent_color=0xffffff)
        bank = ui.Button(label="계좌이체", emoji="<:dot_white:1482000567562928271>")
        bank.callback = self.bank_callback
        gift_card = ui.Button(label="문상결제", emoji="<:dot_white:1482000567562928271>")
        gift_card.callback = self.gift_card_callback
        container.add_item(ui.ActionRow(bank, gift_card))
        self.add_item(container)

    async def bank_callback(self, it): await it.response.send_modal(BankModal())
    async def gift_card_callback(self, it): await it.response.send_modal(CultureModal(bot, LOG_CHANNEL_ID))

class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="한글로 입력", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="숫자만 입력", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        if not re.fullmatch(r'[가-힣]+', self.name.value):
            return await interaction.response.send_message("**입금자명은 한글로만 입력해주세요**", ephemeral=True)
        if not self.amount.value.isdigit():
            return await interaction.response.send_message("**충전금액은 숫자만 입력해주세요**", ephemeral=True)

        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.send_message(view=layout, ephemeral=True)

        # 관리자 로그 채널 전송
        if AUTO_LOG_ENABLED:
            log_chan = bot.get_channel(LOG_CHANNEL_ID)
            if log_chan: 
                await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))

        # 입금 감시 태스크 시작
        asyncio.create_task(self.watch_deposit(interaction, layout, self.name.value, self.amount.value))

    async def watch_deposit(self, interaction, layout, name, amount):
        key = f"{name}_{amount}"
        start_time = time.time()
        while True:
            if time.time() - start_time > 300: # 5분 타임아웃
                if key in pending_deposits: del pending_deposits[key]
                database.update_status(layout.db_id, "시간초과")
                layout.container.clear_items(); layout.container.accent_color = 0xff0000
                layout.container.add_item(ui.TextDisplay("## 입금 시간 초과\n5분 이내 입금이 확인되지 않았습니다."))
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

            await asyncio.sleep(5)
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
                layout.container.clear_items(); layout.container.accent_color = 0x00ff00
                layout.container.add_item(ui.TextDisplay(f"## 충전 완료\n충전금액: {amount_int:,}원"))
                try: await interaction.edit_original_response(view=layout)
                except: pass
                break

class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__(timeout=300)
        self.name, self.amount, self.db_id = name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보"), accent_color=0xffffff)
        self.container.add_item(ui.TextDisplay(
            f"은행: {BANK_CONFIG['bank_name']}\n"
            f"계좌: {BANK_CONFIG['account_num']}\n"
            f"예금주: {BANK_CONFIG['owner']}\n"
            f"금액: {self.amount}원"
        ))
        copy_btn = ui.Button(label="계좌복사", emoji="<:copy:1482673389679415316>")
        copy_btn.callback = self.copy_callback
        self.container.add_item(ui.ActionRow(copy_btn))
        self.add_item(self.container)

    async def copy_callback(self, it: discord.Interaction):
        await it.response.send_message(f"`{BANK_CONFIG['account_num']}`", ephemeral=True)

# --- [3] 시스템 설정: 블랙리스트 및 계좌 설정 ---
async def check_black(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
    cur.execute("SELECT is_blacked FROM users WHERE user_id = ?", (u_id,))
    row = cur.fetchone(); conn.close()
    return True if row and row[0] == 1 else False

class AccountSetupModal(ui.Modal, title="계좌 정보 설정"):
    bank = ui.TextInput(label="은행명", placeholder="예: 카카오뱅크")
    account = ui.TextInput(label="계좌번호", placeholder="하이픈 포함")
    owner = ui.TextInput(label="예금주")

    async def on_submit(self, interaction: discord.Interaction):
        BANK_CONFIG.update({"bank_name": self.bank.value, "account_num": self.account.value, "owner": self.owner.value})
        setup_con = ui.Container(ui.TextDisplay("## 계좌 설정 완료"), accent_color=0x00ff00)
        setup_con.add_item(ui.TextDisplay(f"은행: {self.bank.value}\n계좌: {self.account.value}\n예금주: {self.owner.value}"))
        
        if any(x in self.bank.value for x in ["카카오뱅크", "카뱅"]):
            allow_btn = ui.Button(label="자동충전 허용", style=discord.ButtonStyle.green)
            deny_btn = ui.Button(label="자동충전 거부", style=discord.ButtonStyle.red)
            async def allow_cb(it): 
                global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = False
                await it.response.send_message("**자동충전 허용됨**", ephemeral=True)
            async def deny_cb(it): 
                global AUTO_LOG_ENABLED; AUTO_LOG_ENABLED = True
                await it.response.send_message("**자동충전 거부됨**", ephemeral=True)
            allow_btn.callback, deny_btn.callback = allow_cb, deny_cb
            setup_con.add_item(ui.ActionRow(allow_btn, deny_btn))
            
        await interaction.response.send_message(view=ui.LayoutView().add_item(setup_con), ephemeral=True)
