import discord
from discord import app_commands
from discord.ext import commands, tasks # tasks 추가
import requests

# 전역 변수 설정
current_stock = "0"
target_message = None # 자동 갱신할 메시지 객체 저장용
user_cookie = "" # 쿠키 저장용

class RobuxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="PAY", id=1472159579545796628))
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 프로세스를 시작합니다.", ephemeral=True)

    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="User", id=1472159581017739386))
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_embed = discord.Embed(
            color=0xffffff
        )
        info_embed.set_author(name=f"{interaction.user.name}님의 정보", icon_url=interaction.client.user.display_avatar.url)
        info_embed.add_field(name="누적 금액", value="```0로벅스```", inline=True)
        info_embed.add_field(name="등급 혜택", value="```브론즈 ( 할인 1.5% 적용 )```", inline=True)

        await interaction.response.send_message(embed=info_embed, ephemeral=True)

    @discord.ui.button(label="충전", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="ID", id=1472159578371133615))
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 페이지 안내입니다.", ephemeral=True)

# 쿠키 입력 모달
class CookieModal(discord.ui.Modal, title="로블록스 쿠키 등록"):
    cookie_input = discord.ui.TextInput(
        label="로블록스 쿠키를 입력하세요",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        global user_cookie
        user_cookie = self.cookie_input.value
        await interaction.response.send_message("✅ 쿠키가 등록되었습니다. 이제 1분마다 재고가 자동 갱신됩니다.", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.update_stock_task.start() # 재고 업데이트 태스크 시작

    # 1분마다 실행되는 반복 작업
    @tasks.loop(minutes=1.0)
    async def update_stock_task(self):
        global current_stock, target_message, user_cookie
        
        # 쿠키가 등록되어 있고 갱신할 메시지가 있는 경우에만 실행
        if user_cookie and target_message:
            try:
                url = "https://economy.roblox.com/v1/users/authenticated/currency"
                cookies = {".ROBLOSECURITY": user_cookie}
                response = requests.get(url, cookies=cookies)
                
                if response.status_code == 200:
                    data = response.json()
                    current_stock = f"{data.get('robux', 0):,}"
                    
                    # 새 임베드 생성하여 메시지 수정
                    new_embed = discord.Embed(color=0xffffff)
                    new_embed.set_author(name="자동 로벅스 자판기", icon_url=self.user.display_avatar.url)
                    new_embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
                    new_embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
                    new_embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요 (최근 갱신: 실시간)")
                    
                    await target_message.edit(embed=new_embed)
            except Exception as e:
                print(f"업데이트 오류: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.tree.command(name="쿠키", description="로블록스 쿠키를 설정합니다.")
async def cookie(interaction: discord.Interaction):
    await interaction.response.send_modal(CookieModal())

@bot.tree.command(name="자판기", description="자동화 로벅스 자판기 전송")
async def auto_robux(interaction: discord.Interaction):
    global target_message
    await interaction.response.send_message("**로벅스 자판기를 불러오는 중입니다**", ephemeral=True)
    
    embed = discord.Embed(color=0xffffff)
    embed.set_author(name="자동 로벅스 자판기", icon_url=bot.user.display_avatar.url)
    embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
    embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
    embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요")

    view = RobuxButtons()
    # 전송된 메시지를 변수에 저장하여 나중에 수정 가능하게 함
    target_message = await interaction.followup.send(embed=embed, view=view)

bot.run('YOUR_TOKEN')
