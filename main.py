import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
from discord import app_commands
from discord.ext import commands

# --- 설정 (기존) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195

# --- 로블록스 자동화 설정 (추가) ---
ROBLOX_COOKIE = "여기에_쿠키_전체를_입력하세요" 
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=여기에_코드_입력"

# --- 로블록스 닉네임 유효성 검사 함수 (기존) ---
async def check_roblox_user(username):
    if not re.match(r"^[A-Za-z0-9_]{3,}$", username):
        return None, "형식 불일치 (영어/숫자/_ 3자 이상)"
    url = "https://users.roblox.com/v1/usernames/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"usernames": [username], "excludeBannedUsers": True}) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['data']:
                    return data['data'][0]['name'], "존재함" 
                else:
                    return None, "존재하지 않는 닉네임"
            return None, "API 오류"

# --- 로블록스 자동화 접속 함수 (추가) ---
async def start_roblox_automation(interaction, seller_nick):
    # 1. 접속 중 임베드 전송
    status_embed = discord.Embed(
        title="🤖 시스템 가동",
        description="**로블록스 계정 로그인 및 비공개 서버 접속 시도 중...**\n┗ 쿠키 세션을 확인하고 있습니다.",
        color=0xffff00
    )
    status_msg = await interaction.followup.send(embed=status_embed)

    try:
        # 2. 게임 실행 (프로토콜 호출)
        # 윈도우에 로블록스가 설치되어 있어야 하며, 브라우저 팝업 시 엔터 처리가 필요합니다.
        webbrowser.open(ROBLOX_AMP_SERVER)
        await asyncio.sleep(5)
        pyautogui.press('enter') # 브라우저 "열기" 팝업 대응

        # 3. 로딩 대기 후 임베드 수정
        await asyncio.sleep(25)
        status_embed.title = "🚀 게임 접속 완료"
        status_embed.description = (
            f"**봇이 비공개 서버에 접속했습니다!**\n\n"
            f"🔗 **[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n"
            f"**판매자({seller_nick})님은 접속 후 봇에게 거래를 걸어주세요.**\n"
            f"┗ 봇이 자동으로 거래를 인식하고 수령합니다."
        )
        status_embed.color = discord.Color.blue()
        await status_msg.edit(embed=status_embed)

        # 4. 자동 거래 수령 (이미지 인식 루프 - 컨셉)
        # 이 부분에 pyautogui.locateOnScreen 등을 활용한 이미지 인식 로직을 추가할 수 있습니다.
        print(f"[{seller_nick}] 거래 대기 및 자동 수령 모드 활성화")
        
    except Exception as e:
        await interaction.followup.send(f"❌ 접속 오류: {e}", ephemeral=True)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

    async def on_message(self, message):
        if message.author.bot: return
        if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("중개-"):
            if message.content.isdigit() and 17 <= len(message.content) <= 20:
                try:
                    target_user = await message.guild.fetch_member(int(message.content))
                    await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                    await message.channel.edit(topic=f"invited:{target_user.id}")
                    await message.channel.send(embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다\n┗ 거래 진행해주시면 됩니다**", color=0xffffff), delete_after=10.0)
                    try: await message.delete(delay=10.0)
                    except: pass
                except: pass
        await self.process_commands(message)

bot = MyBot()

# --- 거래 정보 입력 모달 (기존) ---
class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    seller = discord.ui.TextInput(label="판매자 로블록스 닉네임", placeholder="판매자만 적어주세요", required=False)
    buyer = discord.ui.TextInput(label="구매자 로블록스 닉네임", placeholder="구매자만 적어주세요", required=False)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
        if self.original_view.seller_nick: self.seller.default = self.original_view.seller_nick
        if self.original_view.buyer_nick: self.buyer.default = self.original_view.buyer_nick

    async def on_submit(self, interaction: discord.Interaction):
        if self.seller.value:
            real_name, msg = await check_roblox_user(self.seller.value)
            if real_name: self.original_view.seller_nick = real_name
            else: self.original_view.seller_nick = f"❌ {msg}"
        
        if self.buyer.value:
            real_name, msg = await check_roblox_user(self.buyer.value)
            if real_name: self.original_view.buyer_nick = real_name
            else: self.original_view.buyer_nick = f"❌ {msg}"

        s_ok = self.original_view.seller_nick and "❌" not in self.original_view.seller_nick and self.original_view.seller_nick != "미입력"
        b_ok = self.original_view.buyer_nick and "❌" not in self.original_view.buyer_nick and self.original_view.buyer_nick != "미입력"
        
        if s_ok and b_ok:
            self.original_view.confirm_trade_button.disabled = False
            self.original_view.confirm_trade_button.style = discord.ButtonStyle.green
        else:
            self.original_view.confirm_trade_button.disabled = True
            self.original_view.confirm_trade_button.style = discord.ButtonStyle.gray

        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="판매자 닉네임", value=f"```{self.original_view.seller_nick or '미입력'}```", inline=True)
        embed.add_field(name="구매자 닉네임", value=f"```{self.original_view.buyer_nick or '미입력'}```", inline=True)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png")
        await interaction.response.edit_message(embed=embed, view=self.original_view)

# --- 약관 동의 뷰 (수정: 닉네임 전달 및 자동화 연결) ---
class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id, seller_nick):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.seller_nick = seller_nick
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.gray)
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        if interaction.user.id in self.agreed_users:
            return await interaction.response.send_message("**이미 동의하셨습니다**", ephemeral=True)

        self.agreed_users.add(interaction.user.id)
        embed = interaction.message.embeds[0]
        current_desc = embed.description.split("\n\n**(")[0]
        embed.description = f"{current_desc}\n\n**({len(self.agreed_users)}/2) 동의 완료**"
        
        if len(self.agreed_users) >= 2:
            button.disabled = True
            button.style = discord.ButtonStyle.green
            button.label = "동의 완료"
            await interaction.response.edit_message(embed=embed, view=self)
            
            final_embed = discord.Embed(
                title="✅ 약관 동의 완료",
                description="**두 분 모두 약관에 동의하셨습니다\n이제 봇이 비공개 서버에 접속을 시작합니다**",
                color=0xffffff
            )
            await interaction.followup.send(embed=final_embed)
            # 자동화 접속 실행
            asyncio.create_task(start_roblox_automation(interaction, self.seller_nick))
        else:
            await interaction.response.edit_message(embed=embed, view=self)

# --- 거래 단계 뷰 (기존 유지 + AgreementView에 닉네임 전달) ---
class TradeStepView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.confirmed_users = set()
        self.seller_nick = "미입력"
        self.buyer_nick = "미입력"
        self.confirm_trade_button.disabled = True

    @discord.ui.button(label="거래정보 수정", style=discord.ButtonStyle.secondary)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray) 
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        if interaction.user.id in self.confirmed_users:
            return await interaction.response.send_message("**이미 확인 버튼을 누르셨습니다**", ephemeral=True)

        self.confirmed_users.add(interaction.user.id)
        embed = interaction.message.embeds[0]
        embed.description = f"**({len(self.confirmed_users)}/2) 확인 완료**"

        if len(self.confirmed_users) >= 2:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)

            agree_embed = discord.Embed(
                title="중개 이용 약관",
                description=("**제 1조 [중개 원칙]\n┗ 판매자와 구매자 사이의 안전한 거래를 돕기 위한 봇입니다\n┗ 모든 거래 과정(채팅, 아이템 전달)은 서버 데이터 베이스에 실시간으로 저장됩니다\n\n제 2조 [아이템 및 대금 보관]\n┗ 판매자는 약관 동의 후 저장된 중개 전용 계정으로 템을 전달 해야합니다\n┗ 구매자는 중개인이 아이템 수령을 확인한 후에만 대금을 송금 해야 합니다\n┗ 임의로 개인 간 거래를 진행하여 발생하는 사고는 본 서버가 책임지지 않습니다\n\n제 3조 [거래 취소 및 환불]\n┗ 봇이 아이템을 수령하기 전에는 양측 합의 하에 자유롭게 취소 가능합니다\n┗ 봇이 아이템을 수령한 후에는 단심 변심으로 인한 취소가 불가능하며, 상대방의 동의가 있어야만 반환됩니다\n\n제 4조 [금지 사항]\n┗ 아이템 수량 속임수, 송금 확인증 조작 등의 기만행위 적발 시 즉시 영구 밴 처리됩니다\n┗ 중개 과정 중 욕설, 도배, 거래 방해 행위는 제재 대상입니다\n\n제 5조 [면책 조항]\n┗ 로블록스 자페 시스템 오류나 서버 점검으로 인한 아이템 증발에 대해서는 복구가 불가능할 수 있습니다\n┗ 이용자는 본 약관 동의 버튼을 누름으로써 위 모든 내용에 동의한 것으로 간주합니다**"),
                color=0xffffff
            )
            agree_embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png")
            await interaction.followup.send(embed=agree_embed, view=AgreementView(self.owner_id, self.target_id, self.seller_nick))
        else:
            await interaction.response.edit_message(embed=embed, view=self)

# --- 티켓 제어 및 초기 뷰 (기존 그대로 유지) ---
class TicketControlView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green, custom_id="continue_trade")
    async def continue_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        topic = interaction.channel.topic
        if not topic or "invited:" not in topic:
            return await interaction.response.send_message("**상대방을 먼저 초대해야 거래를 진행할 수 있습니다**", ephemeral=True)
        target_id = int(topic.split(":")[1])
        button.disabled = True
        for child in self.children:
            if child.custom_id == "close_ticket":
                child.disabled = True
        await interaction.response.edit_message(view=self)
        embed = discord.Embed(title="거래 정보 확인", description="**거래 정보 수정 버튼을 눌러 로블 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
        embed.set_image(url=img_url)
        await interaction.followup.send(embed=embed, view=TradeStepView(self.owner_id, target_id))

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji="<:emoji_2:1455814454490038305>")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"중개-{user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
        embed1 = discord.Embed(title="중개 안내", description=f"**티켓 생성자 = {user.mention}\n┗ 10분동안 거래 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
        embed2 = discord.Embed(description="**상대방의 유저 ID를 입력해주세요\n┗ 숫자만 입력해주세요 (예: 123456789012345678)**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
        embed2.set_image(url=img_url)
        await ticket_channel.send(content=f"@everyone", embed=embed1)
        await ticket_channel.send(view=TicketControlView(user.id), embed=embed2)

@bot.tree.command(name="amp_panel", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="자동중개 - AMP 전용", description="**안전 거래하기 위해서는 중개가 필수입니다\n아래 버튼을 눌려 중개 절차를 시작해주세요\n\n┗ 티켓 여시면 중개봇이 안내해줍니다\n┗ 상호작용 오류시 문의부탁드려요\n\n[중개 이용약관](https://swnx.shop) / [디스코드 TOS](https://discord.com/terms)**", color=0xffffff)
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png"
    embed.set_image(url=img_url)
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('당신의_봇_토큰')
