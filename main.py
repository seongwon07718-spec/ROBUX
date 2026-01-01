import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
import pytesseract
import os
import numpy as np
from datetime import datetime
from discord import app_commands
from discord.ext import commands

# --- 설정 (기본 유지) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 1455759161039261791
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

# Tesseract OCR 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- [신규] 좌표 및 색상 설정 (coords.txt 기반 수정 필요) ---
# 본인의 화면 좌표와 RGB 값으로 변경하세요.
SCAN_POINT = (773, 432)          # 거래창 감지용 좌표
SCAN_RGB = (160, 179, 184)       # 거래창 감지용 색상 (RGB)
NICK_REGION = (773, 432, 200, 50) # 닉네임 OCR 영역 (x, y, w, h)

ACCEPT_BTN = (1048, 647)         # 거래 요청 '수락' 버튼 좌표
REJECT_BTN = (868, 648)          # 거래 요청 '거절' 버튼 좌표

CONFIRM_1ST = (1028, 687)        # 거래창 내 1차 수락(Accept) 버튼
CONFIRM_2ND = (1046, 685)        # 최종 수락(Confirm) 버튼

# --- 유틸리티 함수 ---
async def check_roblox_user(username):
    if not re.match(r"^[A-Za-z0-9_]{3,}$", username):
        return None, "형식 불일치"
    url = "https://users.roblox.com/v1/usernames/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"usernames": [username], "excludeBannedUsers": True}) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['data']: return data['data'][0]['name'], "존재함"
                else: return None, "존재하지 않음"
            return None, "API 오류"

async def save_log_and_close(channel):
    messages = [f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author.name}: {m.content}" async for m in channel.history(limit=None, oldest_first=True)]
    filename = f"log_{channel.name}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(messages))
    log_ch = channel.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
    if log_ch:
        await log_ch.send(content=f"**중개 완료 로그** | {channel.name}", file=discord.File(filename))
    os.remove(filename)
    await channel.send(embed=discord.Embed(description="**중개가 완료되었습니다\n5분 후 채널이 삭제됩니다**", color=0xffffff))
    await asyncio.sleep(300)
    await channel.delete()

# --- [핵심] 로블록스 자동화 (이미지 인식 제거 버전) ---
async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic else None
    
    # 1. 초기 임베드 전송
    status_embed = discord.Embed(title="접속 중", description="**비공개 서버에 접속하여 봇을 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    # 실제 게임 실행
    webbrowser.open(ROBLOX_AMP_SERVER)
    
    # 20초 대기 후 링크 제공 및 안내 문구 수정
    await asyncio.sleep(20)
    status_embed.description = f"**봇 세팅이 완료되었습니다.**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇에게 거래를 걸어주세요.**\n**구매자(<@{buyer_id}>)님은 봇의 확인 메시지를 기다려주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        # 거래 감지 (픽셀 매칭 + OCR)
        while True:
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=10):
                # 닉네임 확인
                cap = pyautogui.screenshot(region=NICK_REGION)
                detected = pytesseract.image_to_string(cap).strip()
                
                if seller_nick.lower() in detected.lower():
                    pyautogui.click(ACCEPT_BTN) # 수락 클릭
                    break
                else:
                    pyautogui.click(REJECT_BTN) # 거절 클릭
            await asyncio.sleep(0.5)

        # 아이템 검수 단계
        await asyncio.sleep(8) # 아이템 올리는 시간 대기
        pyautogui.screenshot("trade_check.png")
        
        verify_embed = discord.Embed(title="아이템 확인 요청", description=f"**판매자가 올린 아이템이 맞습니까?\n구매자(<@{buyer_id}>)님만 버튼을 눌러주세요.**", color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=ItemVerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"**자동화 중 오류 발생: {e}**", view=CallAdminOnlyView())

# --- 인터페이스 뷰 클래스들 ---

class CallAdminOnlyView(discord.ui.View):
    @discord.ui.button(label="관리자 호출하기", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="warning", id=1455996648571273370))
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"**<@&{ADMIN_ROLE_ID}> 관리자가 오는 중이니 조금만 기다려주세요**")
        await interaction.response.send_message("**관리자를 호출했습니다**", ephemeral=True)

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="아이템이 맞습니다", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji(name="check2", id=1455996406748942501))
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        
        # 봇이 최종 수락 진행
        pyautogui.click(CONFIRM_1ST)
        await asyncio.sleep(5)
        pyautogui.click(CONFIRM_2ND)
        
        embed = discord.Embed(title="송금 단계", description="**봇이 아이템 수령을 완료했습니다\n이제 판매자에게 돈을 송금해 주세요**", color=0xffffff)
        await interaction.response.edit_message(embed=embed, view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="close", id=1455996415976407102))
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        pyautogui.click(REJECT_BTN) # 거래 거부
        await interaction.response.send_message("**아이템 불일치로 거래가 중단되었습니다\n관리자를 호출하세요**", view=CallAdminOnlyView())

class TradeFinalControlView(discord.ui.View):
    def __init__(self, buyer_id):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id

    @discord.ui.button(label="거래완료", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji(name="check2", id=1455996406748942501))
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**모든 거래가 완료되었습니다\n5분 뒤 티켓이 닫힙니다**")
        asyncio.create_task(save_log_and_close(interaction.channel))

    @discord.ui.button(label="거래거파", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="close", id=1455996415976407102))
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**거래가 거파되었습니다\n판매자님은 관리자 호출해 주세요**", view=CallAdminOnlyView())

    @discord.ui.button(label="관리자 호출", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji(name="warning", id=1455996648571273370))
    async def admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"<@&{ADMIN_ROLE_ID}>")

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

class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id, seller_nick):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.seller_nick = seller_nick
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
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
            # 자동화 접속 실행 (내부에서 20초 대기 및 임베드 수정 처리)
            asyncio.create_task(start_roblox_automation(interaction, self.seller_nick))
        else:
            await interaction.response.edit_message(embed=embed, view=self)

class TradeStepView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.confirmed_users = set()
        self.seller_nick = "미입력"
        self.buyer_nick = "미입력"
        self.confirm_trade_button.disabled = True

    @discord.ui.button(label="거래정보 수정", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji(name="quick", id=1455996651218141286))
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="ID", id=1455996414684303471)) 
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
            agree_embed = discord.Embed(title="중개 이용 약관", description="**제 1조 [중개 원칙]...\n(약관 내용 생략)**", color=0xffffff)
            await interaction.followup.send(embed=agree_embed, view=AgreementView(self.owner_id, self.target_id, self.seller_nick))
        else:
            await interaction.response.edit_message(embed=embed, view=self)

class TicketControlView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji=discord.PartialEmoji(name="close", id=1455996415976407102))
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green, custom_id="continue_trade", emoji=discord.PartialEmoji(name="check2", id=1455996406748942501))
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
        embed = discord.Embed(title="거래 정보 확인", description="**거래 정보 수정 버튼을 눌러 로블 닉네임을 적어주세요**", color=0xffffff)
        await interaction.followup.send(embed=embed, view=TradeStepView(self.owner_id, target_id))

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji=discord.PartialEmoji(name="enable", id=1455996417335365643))
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
        await ticket_channel.send(content=f"@everyone", embed=discord.Embed(title="중개 안내", description=f"**티켓 생성자 = {user.mention}**", color=0xffffff))
        await ticket_channel.send(view=TicketControlView(user.id), embed=discord.Embed(description="**상대방의 유저 ID를 입력해주세요**", color=0xffffff))

@bot.tree.command(name="amp_panel", description="입양 중개 패널 전송")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="자동중개 - AMP 전용", description="**안전 거래를 위해 중개를 시작해주세요**", color=0xffffff)
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('YOUR_TOKEN_HERE')
