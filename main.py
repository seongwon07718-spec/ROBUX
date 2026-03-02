import discord
from discord import ui
from discord.ext import commands
import asyncio

intents = discord.Intents.all()
bot = commands.Bot("!", intents=intents)

# 3. 입금 정보 표시 컨테이너 및 타이머
class BankInfoLayout(ui.LayoutView):
    def __init__(self, name, amount):
        super().__init__()
        self.name = name
        self.amount = amount
        self.container = ui.Container(ui.TextDisplay(f"## 입금 정보\n\n**은행명:** OO은행\n**계좌:** 123-456-7890\n**예금주:** 홍길동\n**입금자명:** {self.name}\n**충전금액:** {self.amount}원\n\n-# 5분 이내로 입금해주셔야 충전이 완료됩니다."))
        self.add_item(self.container)

    async def start_timer(self, interaction: discord.Interaction):
        await asyncio.sleep(300)  # 5분(300초) 대기
        
        # 문구 수정
        self.container.clear_items()
        self.container.add_item(ui.TextDisplay("## 충전 시간 초과\n\n자동충전 시간이 초과되었습니다. 다시 시도해 주세요."))
        await interaction.edit_original_response(view=self)

# 2. 계좌이체 모달창
class BankModal(ui.Modal, title="계좌이체 충전"):
    name = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력해주세요.", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전금액", placeholder="금액을 입력해주세요. (숫자만)", min_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        # 모달 제출 시 컨테이너 내용을 입금 정보로 수정
        layout = BankInfoLayout(self.name.value, self.amount.value)
        await interaction.response.edit_message(view=layout)
        # 타이머 시작
        await layout.start_timer(interaction)

# 1. 충전 방식 선택 레이아웃
class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        self.container = ui.Container(ui.TextDisplay("## 충전 방식 선택"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bank = ui.Button(label="계좌이체")
        bank.callback = self.bank_callback
        
        gift_card = ui.Button(label="문화상품권")
        gift_card.callback = self.gift_card_callback
        
        self.container.add_item(ui.ActionRow(bank, gift_card))
        self.add_item(self.container)

    async def bank_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BankModal())

    async def gift_card_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("문화상품권 충전 준비중입니다.", ephemeral=True)

class MeuLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()
        container = ui.Container(ui.TextDisplay("## 구매하기"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("※ 구매전 필독사항\n\n계정 구매 후 환불은 불가능하며 계정 불량 또는 2단계 인증 문제로 로그인 안될 시 문의 부탁드립니다\n\n충전 안될 시 티켓 열고 이중창 제출해주세요 / 오송금은 충전 처리 힘듭니다 계좌, 금액 꼭 확인해주세요\n\n구매하면 디엠으로 제품 전송됩니다 제품 전송 안될 시 DM 허용해주셔야 합니다 / 저희 제품은 최상급으로 지급해드립니다"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        shop = ui.Button(label="제품")
        shop.callback = self.shop_callback
        chage = ui.Button(label="충전")
        chage.callback = self.chage_callback
        buy = ui.Button(label="구매")
        buy.callback = self.buy_callback
        info = ui.Button(label="정보")
        info.callback = self.info_callback

        container.add_item(ui.ActionRow(shop, chage, buy, info))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("-# 봇 오류 뜨거나 문의 사항은 티켓 열어주세요ㅣ24시간 자판기"))
        self.add_item(container)

    async def shop_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def chage_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(view=ChargeLayout(), ephemeral=True)

    async def buy_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def info_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("준비중입니다", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} 온라인')

@bot.tree.command(name="자판기", description="자판기를 출력합니다")
async def jampangi(interaction: discord.Interaction):
    await interaction.response.send_message("자판기가 전송되었습니다.", ephemeral=True)
    await interaction.channel.send(view=MeuLayout())

bot.run("YOUR_TOKEN_HERE")
