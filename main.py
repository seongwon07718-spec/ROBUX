import discord
from discord import ui
from discord.ext import commands
import asyncio
import database  # 위에서 만든 파일 임포트

intents = discord.Intents.all()
bot = commands.Bot("!", intents=intents)

LOG_CHANNEL_ID = 123456789012345678 

# 관리자용 로그 제어
class AdminLogView(ui.LayoutView):
    def __init__(self, user, name, amount, db_id):
        super().__init__()
        self.user, self.name, self.amount, self.db_id = user, name, amount, db_id
        self.container = ui.Container(ui.TextDisplay(f"## 📥 충전 신청 (ID: {db_id})\n\n**신청자:** {user.mention}\n**입금자명:** {name}\n**신청금액:** {amount}원"))
        
        approve_btn = ui.Button(label="완료", style=discord.ButtonStyle.green)
        approve_btn.callback = self.approve_callback
        cancel_btn = ui.Button(label="취소", style=discord.ButtonStyle.red)
        cancel_btn.callback = self.cancel_callback
        
        self.container.add_item(ui.ActionRow(approve_btn, cancel_btn))
        self.add_item(self.container)

    async def approve_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "완료")
        self.container.clear_items()
        self.container.style = discord.ContainerStyle.green
        self.container.add_item(ui.TextDisplay(f"## ✅ 충전 완료\n\n**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}\n**금액:** {self.amount}원"))
        await interaction.response.edit_message(view=self)
        try: await self.user.send(f"✅ 신청하신 {self.amount}원 충전이 완료되었습니다!")
        except: pass

    async def cancel_callback(self, interaction: discord.Interaction):
        database.update_status(self.db_id, "취소")
        self.container.clear_items()
        self.container.style = discord.ContainerStyle.red
        self.container.add_item(ui.TextDisplay(f"## ❌ 충전 취소\n\n**처리자:** {interaction.user.mention}\n**대상:** {self.user.mention}"))
        await interaction.response.edit_message(view=self)

# 유저용 입금 정보 및 타이머
class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount, db_id):
        super().__init__()
        self.db_id = db_id
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보\n\n**은행:** OO은행\n**계좌:** 123-456-7890\n**예금주:** 홍길동\n**입금자:** {name}\n**금액:** {amount}원\n\n-# 5분 내 미입금 시 자동 취소됩니다."))
        self.add_item(self.container)

    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)
        if database.get_status(self.db_id) == "대기":
            database.update_status(self.db_id, "시간초과")
            self.container.clear_items()
            self.container.style = discord.ContainerStyle.red
            self.container.add_item(ui.TextDisplay("## ❌ 충전 시간 초과\n\n자동충전 시간이 초과되었습니다. 다시 시도해 주세요."))
            await interaction.edit_original_response(view=self)

# 계좌이체 모달
class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="성함 입력", min_length=2)
    amount = ui.TextInput(label="충전금액", placeholder="숫자만 입력", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        db_id = database.insert_request(interaction.user.id, self.amount.value)
        layout = BankInfoLayout(self.name.value, self.amount.value, db_id)
        await interaction.response.edit_message(view=layout)
        
        log_chan = bot.get_channel(LOG_CHANNEL_ID)
        if log_chan:
            await log_chan.send(view=AdminLogView(interaction.user, self.name.value, self.amount.value, db_id))
        asyncio.create_task(layout.start_timer(interaction))

# 충전 방식 및 메인 레이아웃 (생략된 구조는 동일)
class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"))
        bank = ui.Button(label="계좌이체")
        bank.callback = lambda i: i.response.send_modal(BankModal())
        container.add_item(ui.ActionRow(bank))
        self.add_item(container)

class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 구매하기"))
        charge = ui.Button(label="충전")
        charge.callback = lambda i: i.response.send_message(view=ChargeLayout(), ephemeral=True)
        container.add_item(ui.ActionRow(charge))
        self.add_item(container)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} 온라인')

@bot.tree.command(name="자판기", description="자판기 출력")
async def jampangi(interaction: discord.Interaction):
    await interaction.response.send_message("자판기가 전송되었습니다.", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())

bot.run("YOUR_TOKEN_HERE")
