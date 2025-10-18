import discord
from discord import PartialEmoji, ui
from discord.ext import commands
intents = discord.Intents.all()

command_prefix = "!"
bot = commands.Bot(command_prefix=command_prefix, intents=intents)

ROLE_ID = 1419336612956864712  # 부여할 역할 ID

class MyLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None) # 뷰 만료 없음

        # 초기 컨테이너: 인증 안내 텍스트와 버튼
        self.c = ui.Container(ui.TextDisplay("인증하기"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.c.add_item(ui.TextDisplay("아래 인증하기 버튼을 눌려 인증해주세요\n인증하시면 모든 채널을 보실 수 있습니다"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        custom_emoji1 = PartialEmoji(name="Right", id=1428996148542181449)

        self.button_1 = ui.Button(label="인증하기", custom_id="button_1", emoji=custom_emoji1)
        # 버튼에 콜백 연결
        self.button_1.callback = self.on_verify_button

        linha = ui.ActionRow(self.button_1)

        self.c.add_item(linha)
        self.add_item(self.c)
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

    async def on_verify_button(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        # 서버 컨텍스트 확인
        if guild is None:
            await interaction.response.send_message("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        role = guild.get_role(ROLE_ID)
        if role is None:
            await interaction.response.send_message("지정된 역할을 찾을 수 없습니다. 서버 설정을 확인해주세요.", ephemeral=True)
            return

        # 이미 역할이 있는지 확인하여 중복 부여 방지
        if role in member.roles:
            await interaction.response.send_message("이미 인증된 사용자입니다. 추가 조치는 필요하지 않습니다.", ephemeral=True)
            return

        # 역할 부여 시도
        try:
            await member.add_roles(role, reason="인증 버튼을 통해 자동 부여")
        except Exception:
            await interaction.response.send_message("역할 부여에 실패했습니다. 봇 권한(역할 관리 및 역할 위치)을 확인해주세요.", ephemeral=True)
            return

        # 에페메럴 컨테이너 생성 및 전송 (누른 사람만 볼 수 있음)
        ephemeral_view = ui.LayoutView(timeout=60)  # 에페메럴 전용 뷰 (타임아웃은 선택사항)
        e_c = ui.Container(ui.TextDisplay("**인증완료**"))
        e_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        e_c.add_item(ui.TextDisplay("역할지급 완료되었습니다\n이제 모든 채널 확인 가능합니다"))
        e_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        ephemeral_view.add_item(e_c)

        # 응답: 에페메럴 메시지 전송 (이 메시지는 누른 사람만 볼 수 있음)
        await interaction.response.send_message(view=ephemeral_view, ephemeral=True)

        # 공개 패널은 그대로 유지 (여러 사람 인증 가능), 따라서 버튼을 비활성화하지 않음

@bot.event
async def on_ready():
    print(f"로벅스 자판기 봇이 {bot.user}로 로그인했습니다.")
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'슬래시 명령어 동기화 중 오류 발생.: {e}')

@bot.tree.command(name="인증패널", description="인증 패널을 표시합니다")
async def button_panel(interaction: discord.Interaction):
    layout = MyLayout()
    await interaction.response.send_message(view=layout, ephemeral=False)

# --- 봇 실행 ---
bot.run("") # 여기에 봇 토큰을 입력하세요
