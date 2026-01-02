import discord
import requests
import random
import string

# 설정값
VERIFIED_ROLE_ID = 123456789012345678 
ROBLOX_USER_SEARCH = "https://users.roblox.com/v1/users/search"
ROBLOX_USER_DETAIL = "https://users.roblox.com/v1/users/"

# 1. 닉네임 입력 모달
class NicknameModal(discord.ui.Modal, title="로블록스 정보 수정"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", placeholder="닉네임을 입력하세요.", min_length=2)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        # 실시간 존재 여부 확인 API
        search = requests.get(ROBLOX_USER_SEARCH, params={"keyword": self.nickname.value, "limit": 1})
        data = search.json().get("data", [])

        if not data:
            self.original_view.roblox_user = None
            status_msg = "❌ 존재하지 않는 이름입니다."
            self.original_view.confirm_btn.disabled = True # 확인 버튼 잠금
        else:
            user = data[0]
            self.original_view.roblox_user = user
            status_msg = f"✅ 확인됨: **{user['name']}** (ID: {user['id']})"
            self.original_view.confirm_btn.disabled = False # 확인 버튼 활성화

        # 임베드 업데이트
        new_embed = discord.Embed(title="인증 정보 수정", color=discord.Color.blue())
        new_embed.add_field(name="현재 입력된 닉네임", value=status_msg)
        new_embed.set_footer(text="이름이 확인되었다면 [인증 완료]를 눌러주세요.")
        
        await interaction.response.edit_message(embed=new_embed, view=self.original_view)

# 2. 정보 수정 및 완료 버튼이 있는 임베드 뷰
class VerifyStepView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roblox_user = None

    @discord.ui.button(label="정보 수정", style=discord.ButtonStyle.gray)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal(self))

    @discord.ui.button(label="인증 완료", style=discord.ButtonStyle.green, disabled=True) # 초기엔 잠금
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 랜덤 문구 생성 및 최종 단계 진행
        verify_key = "FLIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        embed = discord.Embed(title="최종 단계: 프로필 확인", color=discord.Color.gold())
        embed.description = (
            f"**선택된 계정:** {self.roblox_user['name']}\n"
            f"**인증 문구:** `{verify_key}`\n\n"
            f"로블록스 프로필 **소개(About)** 칸에 위 문구를 작성하고 아래 버튼을 눌러주세요."
        )
        
        # 여기서부터는 이전과 동일한 VerifyCheckView(최종 확인 뷰) 호출
        await interaction.response.edit_message(embed=embed, view=VerifyCheckView(self.roblox_user['name'], self.roblox_user['id'], verify_key))

# 3. 초기 /verify 명령어 뷰
class VerifyLaunchView(discord.ui.View):
    @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="인증 정보 수정", description="[정보 수정] 버튼을 눌러 로블록스 닉네임을 입력해주세요.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, view=VerifyStepView(), ephemeral=True)
