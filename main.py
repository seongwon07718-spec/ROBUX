import discord
import asyncio
import aiohttp # 로블록스 API 통신용
import re # 닉네임 정규식 검사
from discord import app_commands
from discord.ext import commands

# 설정
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195

# --- 로블록스 닉네임 유효성 검사 함수 ---
async def check_roblox_user(username):
    # 영어, 숫자, _ 만 허용하며 3글자 이상인지 확인
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

# --- 거래 정보 입력 모달 ---
class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    seller = discord.ui.TextInput(label="판매자 로블록스 닉네임", placeholder="판매자만 적어주세요", required=False)
    buyer = discord.ui.TextInput(label="구매자 로블록스 닉네임", placeholder="구매자만 적어주세요", required=False)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
        if self.original_view.seller_nick: self.seller.default = self.original_view.seller_nick
        if self.original_view.buyer_nick: self.buyer.default = self.original_view.buyer_nick

    async def on_submit(self, interaction: discord.Interaction):
        # 판매자 검사
        if self.seller.value:
            real_name, msg = await check_roblox_user(self.seller.value)
            if real_name: self.original_view.seller_nick = real_name
            else: self.original_view.seller_nick = f"❌ {msg}"
        
        # 구매자 검사
        if self.buyer.value:
            real_name, msg = await check_roblox_user(self.buyer.value)
            if real_name: self.original_view.buyer_nick = real_name
            else: self.original_view.buyer_nick = f"❌ {msg}"

        # 비활성화 오류 해결: 닉네임이 둘 다 "실제 존재"할 때만 비활성화를 풉니다.
        # (문자열에 '❌'가 포함되어 있지 않고 '미입력'이 아닐 때)
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

# --- 약관 동의 뷰 (최종 단계) ---
class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.gray)
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. 거래 당사자 확인
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        # 2. 중복 동의 확인
        if interaction.user.id in self.agreed_users:
            return await interaction.response.send_message("**이미 동의하셨습니다**", ephemeral=True)

        self.agreed_users.add(interaction.user.id)
        
        # 3. 임베드 현황 업데이트 (본문 하단에 표시)
        embed = interaction.message.embeds[0]
        # 기존 설명글 유지하면서 하단에 현황만 업데이트 (기존 현황 텍스트가 쌓이지 않게 처리)
        current_desc = embed.description.split("\n\n**(")[0] # 기존 약관 내용만 추출
        embed.description = f"{current_desc}\n\n**({len(self.agreed_users)}/2) 동의 완료**"
        
        if len(self.agreed_users) >= 2:
            # 두 명 모두 동의 완료 시
            button.disabled = True
            button.style = discord.ButtonStyle.green
            button.label = "동의 완료"
            
            # 버튼 상태 변경 반영
            await interaction.response.edit_message(embed=embed, view=self)
            
            # 최종 완료 임베드 전송
            final_embed = discord.Embed(
                title="약관 동의 완료",
                description="**두 분 모두 약관에 동의하셨습니다\n이제 봇이 아이템을 전달받을 준비를 합니다**",
                color=0xffffff
            )
            await interaction.followup.send(embed=final_embed)
        else:
            # 한 명만 동의했을 때 (1/2 표시)
            await interaction.response.edit_message(embed=embed, view=self)

# --- 거래 단계 뷰 ---
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
        
        # 현황 업데이트 (1/2 -> 2/2)
        embed = interaction.message.embeds[0]
        embed.description = f"**({len(self.confirmed_users)}/2) 확인 완료**"

        if len(self.confirmed_users) >= 2:
            # 2/2가 되었을 때
            for child in self.children:
                child.disabled = True
            # 먼저 2/2로 바뀐 임베드와 비활성화된 버튼을 보여줌
            await interaction.response.edit_message(embed=embed, view=self)

            # 그 후 약관 임베드 전송
            agree_embed = discord.Embed(
                title="중개 이용 약관",
                description=("**제 1조 [중개 원칙]\n┗ 판매자와 구매자 사이의 안전한 거래를 돕기 위한 봇입니다\n┗ 모든 거래 과정(채팅, 아이템 전달)은 서버 데이터 베이스에 실시간으로 저장됩니다\n\n제 2조 [아이템 및 대금 보관]\n┗ 판매자는 약관 동의 후 저장된 중개 전용 계정으로 템을 전달 해야합니다\n┗ 구매자는 중개인이 아이템 수령을 확인한 후에만 대금을 송금 해야 합니다\n┗ 임의로 개인 간 거래를 진행하여 발생하는 사고는 본 서버가 책임지지 않습니다\n\n제 3조 [거래 취소 및 환불]\n┗ 봇이 아이템을 수령하기 전에는 양측 합의 하에 자유롭게 취소 가능합니다\n┗ 봇이 아이템을 수령한 후에는 단심 변심으로 인한 취소가 불가능하며, 상대방의 동의가 있어야만 반환됩니다\n\n제 4조 [금지 사항]\n┗ 아이템 수량 속임수, 송금 확인증 조작 등의 기만행위 적발 시 즉시 영구 밴 처리됩니다\n┗ 중개 과정 중 욕설, 도배, 거래 방해 행위는 제재 대상입니다\n\n제 5조 [면책 조항]\n┗ 로블록스 자페 시스템 오류나 서버 점검으로 인한 아이템 증발에 대해서는 복구가 불가능할 수 있습니다\n┗ 이용자는 본 약관 동의 버튼을 누름으로써 위 모든 내용에 동의한 것으로 간주합니다**"),
                color=0xffffff
            )
            agree_embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png")
            
            await interaction.followup.send(embed=agree_embed, view=AgreementView(self.owner_id, self.target_id))
        else:
            # 1/2일 때
            await interaction.response.edit_message(embed=embed, view=self)

# --- 티켓 제어 뷰 (초기) ---
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
        # 상대방 초대 여부 확인 (Topic에 저장된 ID 추출)
        topic = interaction.channel.topic
        if not topic or "invited:" not in topic:
            return await interaction.response.send_message("**상대방을 먼저 초대해야 거래를 진행할 수 있습니다**", ephemeral=True)
        
        target_id = int(topic.split(":")[1])
        
        # 버튼 상태 변경
        button.disabled = True
        # 티켓닫기 버튼 찾아서 비활성화 (보통 첫 번째 버튼)
        for child in self.children:
            if child.custom_id == "close_ticket":
                child.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # 새 거래 진행 임베드와 버튼 전송
        embed = discord.Embed(
            title="거래 정보 확인",
            description="**거래 정보 수정 버튼을 눌러 로블 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**",
            color=0xffffff
        )
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
    bot.run('')
