import discord
from discord import app_commands
from discord.ext import commands
import checker
import io

TOKEN = "YOUR_TOKEN"
ROLE_ID = 1234567890  # 무료체커를 사용할 수 있는 역할 ID

class CheckerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CheckerBot()

# --- 모달창 (소량 체커) ---
class SingleCookieModal(discord.ui.Modal, title='소량 쿠키 체커'):
    cookie_input = discord.ui.TextInput(label='쿠키를 입력하세요', placeholder='_|WARNING:-DO-NOT-SHARE-...', style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("체킹 중...", ephemeral=True)
        result = await checker.fetch_all(self.cookie_input.value)
        
        if result:
            embed = discord.Embed(title="체커 결과", color=0x00ff00)
            embed.add_field(name="유저명", value=result['name'])
            embed.add_field(name="Robux", value=result['robux'])
            embed.add_field(name="Premium", value=result['premium'])
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            await interaction.edit_original_response(content="유효하지 않은 쿠키입니다.")

# --- 메뉴 선택 뷰 ---
class CheckerSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="소량 체커", style=discord.ButtonStyle.primary)
    async def single_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SingleCookieModal())

    @discord.ui.button(label="대량 체커", style=discord.ButtonStyle.secondary)
    async def multi_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("체크할 쿠키가 담긴 .txt 파일을 DM으로 보내주세요!", ephemeral=True)
        # DM 유도 로직 (이후 DM 이벤트에서 처리)

# --- 메인 시작 뷰 ---
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="무료 체커", style=discord.ButtonStyle.success)
    async def free_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 역할 확인
        role = interaction.guild.get_role(ROLE_ID)
        if role not in interaction.user.roles:
            return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
        
        embed = discord.Embed(title="기능을 선택해주세요", description="원하시는 체커 모드를 선택하세요.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=CheckerSelectView(), ephemeral=True)

    @discord.ui.button(label="유료 체커", style=discord.ButtonStyle.danger)
    async def paid_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("준비 중인 기능입니다.", ephemeral=True)

@bot.tree.command(name="체커기", description="쿠키 체커 메뉴를 엽니다.")
async def checker_menu(interaction: discord.Interaction):
    embed = discord.Embed(title="쿠키 체커 시스템", description="아래 버튼을 눌러 시작하세요.", color=0x2b2d31)
    await interaction.response.send_message(embed=embed, view=MainView())

# --- 대량 체커 DM 처리 ---
@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and message.attachments and not message.author.bot:
        attachment = message.attachments[0]
        if attachment.filename.endswith('.txt'):
            await message.author.send("파일을 분석 중입니다. 잠시만 기다려주세요...")
            
            content = await attachment.read()
            cookies = content.decode('utf-8').splitlines()
            
            valid_results = []
            for cookie in cookies:
                res = await checker.fetch_all(cookie.strip())
                if res:
                    valid_results.append(f"유저: {res['name']} | Robux: {res['robux']}")

            result_text = "\n".join(valid_results) if valid_results else "유효한 쿠키가 없습니다."
            
            # 결과가 길면 파일로 전송
            if len(result_text) > 1900:
                with io.BytesIO(result_text.encode()) as f:
                    await message.author.send("체크 완료! 결과 파일입니다:", file=discord.File(f, "results.txt"))
            else:
                await message.author.send(f"**[체크 완료]**\n{result_text}")

    await bot.process_commands(message)

bot.run(TOKEN)
