import discord
from discord import ui
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.all()
bot = commands.Bot("!", intents=intents)

# 충전 버튼 클릭 시 나타날 새로운 레이아웃 (계좌이체, 문화상품권)
class ChargeLayout(ui.LayoutView):
    def __init__(self):
        super().__init__()

        container = ui.Container(ui.TextDisplay("## 충전 방식 선택"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("원하시는 충전 수단을 선택해주세요."))
        
        bank = ui.Button(label="계좌이체")
        bank.callback = self.bank_callback
        
        gift_card = ui.Button(label="문화상품권")
        gift_card.callback = self.gift_card_callback
        
        button_row = ui.ActionRow(bank, gift_card)
        container.add_item(button_row)
        self.add_item(container)

    async def bank_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("계좌이체 충전 준비중입니다.", ephemeral=True)

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

        button = ui.ActionRow(shop, chage, buy, info)
        container.add_item(button)
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay("-# 봇 오류 뜨거나 문의 사항은 티켓 열어주세요ㅣ24시간 자판기"))
        self.add_item(container)

    async def shop_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def chage_callback(self, interaction: discord.Interaction):
        # 충전 버튼 클릭 시 새로운 컨테이너(ChargeLayout)를 나에게만 보이게 전송
        layout = ChargeLayout()
        await interaction.response.send_message(view=layout, ephemeral=True)

    async def buy_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message("준비중입니다", ephemeral=True)

    async def info_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message("준비중입니다", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} 온라인')

@bot.tree.command(name="자판기", description="자판기를 출력합니다")
async def jampangi(interaction: discord.Interaction):
    await interaction.response.send_message("자판기가 전송되었습니다.", ephemeral=True)
    layout = MeuLayout()
    await interaction.channel.send(view=layout)

bot.run("YOUR_TOKEN_HERE")
