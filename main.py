import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

# 전역 변수
current_stock = "0"
target_message = None 
user_cookie = ""

class RobuxButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="구매", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="PAY", id=1472159579545796628))
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("구매 프로세스를 시작합니다.", ephemeral=True)

    @discord.ui.button(label="내 정보", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="User", id=1472159581017739386))
    async def info(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_embed = discord.Embed(color=0xffffff)
        info_embed.set_author(name=f"{interaction.user.name}님의 정보", icon_url=interaction.client.user.display_avatar.url)
        info_embed.add_field(name="누적 금액", value="```0로벅스```", inline=True)
        info_embed.add_field(name="등급 혜택", value="```브론즈 ( 할인 1.5% 적용 )```", inline=True)
        await interaction.response.send_message(embed=info_embed, ephemeral=True)

    @discord.ui.button(label="충전", style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji(name="ID", id=1472159578371133615))
    async def charge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("충전 페이지 안내입니다.", ephemeral=True)

class CookieModal(discord.ui.Modal, title="로블록스 쿠키 등록"):
    cookie_input = discord.ui.TextInput(
        label="로블록스 쿠키를 입력하세요",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        global user_cookie, current_stock
        user_cookie = self.cookie_input.value
        
        try:
            # 유저 정보 가져오기 API
            cookies = {".ROBLOSECURITY": user_cookie}
            user_res = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies)
            economy_res = requests.get("https://economy.roblox.com/v1/users/authenticated/currency", cookies=cookies)
            
            if user_res.status_code == 200 and economy_res.status_code == 200:
                user_data = user_res.json()
                economy_data = economy_res.json()
                
                name = user_data.get("name", "알 수 없음")
                robux = economy_data.get("robux", 0)
                premium = "보유 중" if user_data.get("isPremium", False) else "미보유"
                current_stock = f"{robux: private,}"

                # 나에게만 보이는 상세 정보 임베드
                success_embed = discord.Embed(title="✅ 쿠키 등록 및 로그인 성공", color=0x00ff00)
                success_embed.add_field(name="닉네임", value=f"```{name}```", inline=True)
                success_embed.add_field(name="보유 로벅스", value=f"```{robux:,} R$```", inline=True)
                success_embed.add_field(name="프리미엄", value=f"```{premium}```", inline=True)
                success_embed.set_footer(text="이 메시지는 본인에게만 보입니다.")
                
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
                
                # 등록 즉시 자판기 임베드 1회 강제 갱신
                if target_message:
                    new_embed = discord.Embed(color=0xffffff)
                    new_embed.set_author(name="자동 로벅스 자판기", icon_url=interaction.client.user.display_avatar.url)
                    new_embed.add_field(name="현재 재고", value=f"```{robux:,}로벅스```", inline=True)
                    new_embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
                    new_embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요 (실시간 갱신 중)")
                    await target_message.edit(embed=new_embed)
            else:
                await interaction.response.send_message("❌ 로그인 실패: 쿠키가 올바르지 않습니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ 오류 발생: {e}", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.refresh_stock.start()

    @tasks.loop(seconds=60.0)
    async def refresh_stock(self):
        global current_stock, target_message, user_cookie
        if user_cookie and target_message:
            try:
                cookies = {".ROBLOSECURITY": user_cookie}
                response = requests.get("https://economy.roblox.com/v1/users/authenticated/currency", cookies=cookies)
                if response.status_code == 200:
                    current_stock = f"{response.json().get('robux', 0):,}"
                    new_embed = discord.Embed(color=0xffffff)
                    new_embed.set_author(name="자동 로벅스 자판기", icon_url=self.user.display_avatar.url)
                    new_embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
                    new_embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
                    new_embed.set_footer(text="안내: 문제 발생 시 관리자에게 문의해주세요 (실시간 갱신 중)")
                    await target_message.edit(embed=new_embed)
            except:
                pass

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.tree.command(name="쿠키", description="로블록스 쿠키를 등록하고 정보를 확인합니다.")
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
    target_message = await interaction.followup.send(embed=embed, view=view)

bot.run('YOUR_TOKEN')
