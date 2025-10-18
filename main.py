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
        # 버튼 누른 사용자에게 역할 부여 시도
        member = interaction.user
        guild = interaction.guild

        # 상호작용 응답이 필요한 경우, defer를 사용해 응답 시간을 벌 수 있음
        await interaction.response.defer(ephemeral=False, thinking=True)

        if guild is None:
            # 길드(서버) 컨텍스트가 아닌 경우
            await interaction.followup.send("이 명령은 서버에서만 사용할 수 있습니다.", ephemeral=True)
            return

        role = guild.get_role(ROLE_ID)
        if role is None:
            await interaction.followup.send("지정된 역할을 찾을 수 없습니다. 서버 설정을 확인해주세요.", ephemeral=True)
            return

        try:
            # 역할 부여
            await member.add_roles(role, reason="인증 버튼을 통해 자동 부여")
        except Exception as e:
            # 권한 문제 등으로 실패할 경우
            await interaction.followup.send("역할 부여에 실패했습니다. 봇 권한을 확인해주세요.", ephemeral=True)
            return

        # 역할 부여 성공 시 뷰 업데이트: 기존 컨테이너 내용을 교체하여 '인증완료' 메시지 표시
        # 새로 교체할 컨테이너 생성
        new_c = ui.Container(ui.TextDisplay("**인증완료**"))
        new_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        new_c.add_item(ui.TextDisplay("역할지급 완료되었습니다\n이제 모든 채널 확인 가능합니다"))
        new_c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 뷰 내 아이템을 새 컨테이너로 교체
        # 먼저 기존 아이템들을 모두 비우고 새 컨테이너로 대체
        self.clear_items()
        self.add_item(new_c)

        # 메시지 편집(원래 보낸 메시지를 업데이트) — interaction.followup.edit_message 사용
        try:
            # interaction.message가 None일 수도 있으므로 안전하게 처리
            if interaction.message:
                await interaction.message.edit(view=self)
            else:
                # 만약 interaction.message가 없다면 새로 메시지로 응답
                await interaction.followup.send(view=self)
        except Exception:
            # 편집에 실패해도 유저에게 완료 안내는 보냄
            await interaction.followup.send("역할이 정상적으로 지급되었습니다. (메시지 업데이트에 실패함)", ephemeral=False)

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
