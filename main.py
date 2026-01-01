import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
import pytesseract
import os
import cv2
import numpy as np
from datetime import datetime
from discord import app_commands
from discord.ext import commands

# --- [1. 설정 및 좌표 고정] ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 1455759161039261791
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

# Tesseract OCR 경로 (본인 PC 경로에 맞게 수정 필요)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 좌표 (coords.txt에서 확인한 좌표로 수정해서 사용하세요)
SCAN_POINT = (773, 432)          
SCAN_RGB = (160, 179, 184)       
NICK_REGION = (773, 432, 250, 60) 

ACCEPT_BTN = (1048, 647)         
REJECT_BTN = (868, 648)          

CONFIRM_1ST_BTN = (1028, 687)    
CONFIRM_2ND_BTN = (1046, 685)    

# --- [2. 유틸리티 및 OCR 함수] ---

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

def get_refined_nickname(region):
    """이미지 전처리를 통해 판독률을 극대화 (흑백 전환 + 확대)"""
    screenshot = pyautogui.screenshot(region=region)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    custom_config = r'--oem 3 --psm 7'
    text = pytesseract.image_to_string(resized, config=custom_config, lang='eng')
    return "".join(filter(str.isalnum, text)).lower()

async def save_log_and_close(channel):
    messages = []
    async for m in channel.history(limit=None, oldest_first=True):
        messages.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author.name}: {m.content}")
    
    filename = f"log_{channel.name}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(messages))
    
    log_ch = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if log_ch:
        await log_ch.send(content=f"**중개 완료 로그** | {channel.name}", file=discord.File(filename))
    
    if os.path.exists(filename):
        os.remove(filename)
    
    await channel.send(embed=discord.Embed(description="**중개가 완료되었습니다\n5분 후 채널이 삭제됩니다**", color=0xffffff))
    await asyncio.sleep(300)
    try: await channel.delete()
    except: pass

# --- [3. 자동화 핵심 로직] ---

async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = None
    if channel.topic and "invited:" in channel.topic:
        buyer_id = int(channel.topic.split(":")[1])
    
    status_embed = discord.Embed(title="접속 중", description="**비공개 서버에 접속하여 자동화를 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    webbrowser.open(ROBLOX_AMP_SERVER)
    await asyncio.sleep(20) # 20초 대기

    status_embed.description = f"**봇 세팅 완료!**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇에게 거래를 걸어주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        while True:
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=25):
                detected_name = get_refined_nickname(NICK_REGION)
                if seller_nick.lower() in detected_name:
                    pyautogui.click(ACCEPT_BTN)
                    break
                else:
                    if len(detected_name) > 2:
                        pyautogui.click(REJECT_BTN)
            await asyncio.sleep(0.5)

        await asyncio.sleep(8) 
        pyautogui.screenshot("trade_check.png")
        
        verify_embed = discord.Embed(title="📦 아이템 확인", description=f"**판매자가 올린 아이템이 맞습니까?\n구매자(<@{buyer_id}>)님만 아래 버튼을 눌러주세요.**", color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=ItemVerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"**자동화 오류 발생: {e}**", view=CallAdminOnlyView())

# --- [4. 뷰(View) 클래스 및 인터페이스] ---

class CallAdminOnlyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="관리자 호출하기", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"**<@&{ADMIN_ROLE_ID}> 관리자가 호출되었습니다.**")
        await interaction.response.send_message("관리자를 호출했습니다.", ephemeral=True)

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="아이템이 맞습니다", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id:
            return await interaction.response.send_message("구매자만 누를 수 있습니다.", ephemeral=True)
        
        await interaction.response.send_message("구매자 확인 완료. 봇이 수락을 진행합니다.")
        
        # 1차/2차 즉시 수락 로직
        pyautogui.click(CONFIRM_1ST_BTN)
        await asyncio.sleep(5)
        pyautogui.click(CONFIRM_2ND_BTN)
        
        await interaction.channel.send(embed=discord.Embed(title="수령 완료", description="**봇이 수령을 마쳤습니다. 판매자에게 송금해주세요.**", color=0xffffff), view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        pyautogui.click(REJECT_BTN)
        await interaction.response.send_message("아이템 불일치로 거절되었습니다.", view=CallAdminOnlyView())

class TradeFinalControlView(discord.ui.View):
    def __init__(self, buyer_id):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id

    @discord.ui.button(label="거래완료", style=discord.ButtonStyle.success, emoji="✅")
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**모든 거래가 완료되었습니다. 5분 뒤 채널이 삭제됩니다.**")
        asyncio.create_task(save_log_and_close(interaction.channel))

    @discord.ui.button(label="거래거파", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**거래가 중단되었습니다.**", view=CallAdminOnlyView())

class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    seller = discord.ui.TextInput(label="판매자 로블록스 닉네임", placeholder="정확하게 입력")
    buyer = discord.ui.TextInput(label="구매자 로블록스 닉네임", placeholder="정확하게 입력")

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        s_name, s_msg = await check_roblox_user(self.seller.value)
        b_name, b_msg = await check_roblox_user(self.buyer.value)
        
        self.original_view.seller_nick = s_name if s_name else f"❌ {s_msg}"
        self.original_view.buyer_nick = b_name if b_name else f"❌ {b_msg}"

        if s_name and b_name:
            self.original_view.confirm_trade_button.disabled = False
            self.original_view.confirm_trade_button.style = discord.ButtonStyle.green
        
        embed = discord.Embed(title="정보 확인", color=0xffffff)
        embed.add_field(name="판매자", value=f"```{self.original_view.seller_nick}```")
        embed.add_field(name="구매자", value=f"```{self.original_view.buyer_nick}```")
        await interaction.response.edit_message(embed=embed, view=self.original_view)

class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id, seller_nick):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.seller_nick = seller_nick
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.green, emoji="📜")
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("당사자만 가능합니다.", ephemeral=True)
        
        self.agreed_users.add(interaction.user.id)
        if len(self.agreed_users) >= 2:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("**양측 동의 완료. 자동화를 시작합니다.**")
            asyncio.create_task(start_roblox_automation(interaction, self.seller_nick))
        else:
            await interaction.response.send_message(f"**{interaction.user.display_name}님 동의 완료 (1/2)**")

class TradeStepView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.seller_nick = "미입력"
        self.buyer_nick = "미입력"
        self.confirmed = set()

    @discord.ui.button(label="정보 입력", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray, disabled=True)
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed.add(interaction.user.id)
        if len(self.confirmed) >= 2:
            await interaction.response.send_message("약관을 확인해주세요.", view=AgreementView(self.owner_id, self.target_id, self.seller_nick))
        else:
            await interaction.response.send_message(f"확인 대기 중.. ({len(self.confirmed)}/2)", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

    @discord.ui.button(label="거래진행", style=discord.ButtonStyle.green)
    async def proceed(self, interaction: discord.Interaction, button: discord.ui.Button):
        topic = interaction.channel.topic
        if not topic or "invited:" not in topic:
            return await interaction.response.send_message("상대방을 먼저 초대하세요.", ephemeral=True)
        target_id = int(topic.split(":")[1])
        await interaction.response.send_message("거래 정보를 입력하세요.", view=TradeStepView(self.owner_id, target_id))

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="중개문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket = await guild.create_text_channel(name=f"중개-{interaction.user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"{ticket.mention}이 생성되었습니다.", ephemeral=True)
        await ticket.send(f"{interaction.user.mention}님, 상대방의 ID를 입력해 초대하세요.", view=TicketControlView(interaction.user.id))

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_message(self, message):
        if message.author.bot: return
        if message.channel.name and message.channel.name.startswith("중개-"):
            if message.content.isdigit():
                try:
                    target = await message.guild.fetch_member(int(message.content))
                    await message.channel.set_permissions(target, read_messages=True, send_messages=True)
                    await message.channel.edit(topic=f"invited:{target.id}")
                    await message.channel.send(f"**{target.mention}님이 초대되었습니다.**")
                except: pass
        await self.process_commands(message)

bot = MyBot()

@bot.tree.command(name="amp_panel")
async def escrow_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="자동중개 시스템", description="아래 버튼을 눌러 티켓을 생성하세요.", color=0xffffff)
    await interaction.response.send_message(embed=embed, view=EscrowView())

if __name__ == "__main__":
    bot.run('YOUR_TOKEN_HERE')
