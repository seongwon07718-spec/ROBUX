import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests
import re

# 전역 변수
current_stock = "0"
target_message = None 
user_cookie = ""

# 실제 브라우저처럼 보이게 하는 필수 헤더
def get_roblox_headers(cookie=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com"
    }
    if cookie:
        # 쿠키 값 앞에 .ROBLOSECURITY= 가 붙어있는지 확인 후 설정
        formatted_cookie = cookie if ".ROBLOSECURITY=" in cookie else f".ROBLOSECURITY={cookie}"
        headers["Cookie"] = formatted_cookie
    return headers

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

class CookieModal(discord.ui.Modal, title="강력한 쿠키 등록 시스템"):
    cookie_input = discord.ui.TextInput(
        label="로블록스 쿠키 (전체 복사해서 넣으세요)",
        placeholder="_|WARNING:-DO-NOT-SHARE-THIS...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        global user_cookie, current_stock
        raw_val = self.cookie_input.value.strip()

        # 1. 쿠키 값만 정확히 추출 (정규식 보강)
        match = re.search(r"(_\|WARNING:-DO-NOT-SHARE-THIS[^;]+)", raw_val)
        clean_cookie = match.group(1) if match else raw_val
        
        user_cookie = clean_cookie
        session = requests.Session()
        session.headers.update(get_roblox_headers(user_cookie))

        try:
            # 2. 보안 토큰(CSRF) 우회 시도
            logout_res = session.post("https://auth.roblox.com/v2/logout")
            csrf_token = logout_res.headers.get("x-csrf-token")
            if csrf_token:
                session.headers.update({"x-csrf-token": csrf_token})

            # 3. 유저 정보 및 로벅스 확인
            user_info = session.get("https://users.roblox.com/v1/users/authenticated").json()
            user_id = user_info.get("id")
            
            if user_id:
                name = user_info.get("name")
                economy = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency").json()
                robux = economy.get("robux", 0)
                current_stock = f"{robux:,}"

                # 성공 알림
                res_embed = discord.Embed(title="✅ 쿠키 인증 및 보안 우회 성공", color=0x00ff00)
                res_embed.add_field(name="계정명", value=f"```{name}```", inline=True)
                res_embed.add_field(name="보유 로벅스", value=f"```{current_stock} R$```", inline=True)
                await interaction.response.send_message(embed=res_embed, ephemeral=True)

                # 즉시 자판기 업데이트
                if target_message:
                    upd_embed = discord.Embed(color=0xffffff)
                    upd_embed.set_author(name="자동 로벅스 자판기", icon_url=interaction.client.user.display_avatar.url)
                    upd_embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
                    upd_embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
                    await target_message.edit(embed=upd_embed)
            else:
                await interaction.response.send_message("❌ 인증 실패: 쿠키가 올바르지 않거나 IP가 차단되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ 에러 발생: {e}", ephemeral=True)

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
                session = requests.Session()
                session.headers.update(get_roblox_headers(user_cookie))
                res = session.get("https://economy.roblox.com/v1/users/authenticated/currency")
                if res.status_code == 200:
                    current_stock = f"{res.json().get('robux', 0):,}"
                    new_embed = discord.Embed(color=0xffffff)
                    new_embed.set_author(name="자동 로벅스 자판기", icon_url=self.user.display_avatar.url)
                    new_embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
                    new_embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
                    await target_message.edit(embed=new_embed)
            except: pass

bot = MyBot()

@bot.tree.command(name="쿠키", description="로블록스 쿠키 등록")
async def cookie(interaction: discord.Interaction):
    await interaction.response.send_modal(CookieModal())

@bot.tree.command(name="자판기", description="자동화 자판기 전송")
async def auto_robux(interaction: discord.Interaction):
    global target_message
    await interaction.response.send_message("로딩 중...", ephemeral=True)
    embed = discord.Embed(color=0xffffff)
    embed.set_author(name="자동 로벅스 자판기", icon_url=bot.user.display_avatar.url)
    embed.add_field(name="현재 재고", value=f"```{current_stock}로벅스```", inline=True)
    embed.add_field(name="현재 가격", value="```만원 = 1300로벅스```", inline=True)
    target_message = await interaction.followup.send(embed=embed, view=RobuxButtons())

bot.run('YOUR_TOKEN')
