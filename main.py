import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
import pytesseract
import os
from discord import app_commands
from discord.ext import commands

# --- [1. 기본 설정 - 기존 내용 유지] ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 123456789012345678 # 로그 채널 ID 입력 필수
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"
IMG_PATH = "images/"

# 사진에 나온 Tesseract 설치 경로 반영
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- [2. 필수 함수 정의 - 이 함수들이 위에 있어야 오류가 안 납니다] ---

async def check_roblox_user(username):
    """로블록스 유저 유효성 검사 (오류 해결용)"""
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
    """대화 로그 저장 및 티켓 삭제"""
    messages = [f"{m.author.name}: {m.content}" async for m in channel.history(limit=None, oldest_first=True)]
    filename = f"log_{channel.id}.txt"
    with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(messages))
    log_ch = channel.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
    if log_ch: await log_ch.send(file=discord.File(filename))
    os.remove(filename)
    await asyncio.sleep(300)
    await channel.delete()

# --- [3. 로블록스 자동화 핵심 (PNG 11종 기능 싹 다 포함)] ---

async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic else None
    
    status_embed = discord.Embed(title="접속중", description="**비공개 서버에 접속 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    try:
        # 게임 실행
        webbrowser.open(ROBLOX_AMP_SERVER)
        await asyncio.sleep(5); pyautogui.press('enter')
        await asyncio.sleep(40) 

        # 1. 초기 팝업 및 입장 (play_button, close_button)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}play_button.png', confidence=0.8))
        await asyncio.sleep(5)
        for _ in range(3):
            btn = pyautogui.locateOnScreen(f'{IMG_PATH}close_button.png', confidence=0.7)
            if btn: pyautogui.click(btn); await asyncio.sleep(1)

        # 2. 이동 (backpack_icon, gifts_tab, plus_icon, yes_button)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}backpack_icon.png', confidence=0.8))
        await asyncio.sleep(1)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}gifts_tab.png', confidence=0.8))
        await asyncio.sleep(1)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}plus_icon.png', confidence=0.8))
        await asyncio.sleep(1)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}yes_button.png', confidence=0.8))

        # 3. 거래 대기 및 선별 수락 (trade_popup_area, accept_request, reject_other)
        status_embed.title = "거래 대기"
        status_embed.description = f"**[{seller_nick}]** 님의 요청만 수락합니다.\n관리자 호출 버튼은 항상 활성화되어 있습니다."
        await status_msg.edit(embed=status_embed, view=AdminCallView())

        while True:
            popup = pyautogui.locateOnScreen(f'{IMG_PATH}trade_popup_area.png', confidence=0.7)
            if popup:
                x, y, w, h = popup
                # 판매자 이름 인식
                cap = pyautogui.screenshot(region=(x + 70, y + 30, 200, 50))
                name = pytesseract.image_to_string(cap).strip()
                if seller_nick.lower() in name.lower():
                    pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}accept_request.png', confidence=0.8))
                    break
                else:
                    pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}reject_other.png', confidence=0.8))
            await asyncio.sleep(1)

        # 4. 검수 (스크린샷 전송 및 버튼 생성)
        await asyncio.sleep(10)
        pyautogui.screenshot("trade_check.png")
        verify_embed = discord.Embed(title="📦 아이템 확인", description="구매 아이템이 맞는지 확인해 주세요.", color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=VerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"❌ 오류 발생: {e}", view=AdminCallView())

# --- [4. 인터페이스 및 기존 클래스 정의] ---

class AdminCallView(discord.ui.View):
    @discord.ui.button(label="관리자 호출", style=discord.ButtonStyle.danger, emoji="🆘")
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"<@&{ADMIN_ROLE_ID}> 관리자 호출 접수!")
        await interaction.response.send_message("관리자를 호출했습니다.", ephemeral=True)

class VerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="예, 구매 아이템이 맞습니다", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        # 봇이 최종 수락 (confirm_trade, final_accept)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}confirm_trade.png', confidence=0.8))
        await asyncio.sleep(5)
        pyautogui.click(pyautogui.locateCenterOnScreen(f'{IMG_PATH}final_accept.png', confidence=0.8))
        
        await interaction.response.edit_message(content="✅ 수령 완료! 대금을 송금해 주세요.", view=FinalControlView(self.buyer_id))

class FinalControlView(discord.ui.View):
    def __init__(self, buyer_id):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id

    @discord.ui.button(label="거래완료", style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎊 중개 완료! 로그 저장 후 5분 뒤 삭제됩니다.")
        asyncio.create_task(save_log_and_close(interaction.channel))

    @discord.ui.button(label="관리자 호출", style=discord.ButtonStyle.secondary, emoji="🆘")
    async def admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"<@&{ADMIN_ROLE_ID}> 관리자 호출!")

# --- [5. 봇 클래스 정의 및 실행 - MyBot 오류 해결] ---

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot() # 클래스 정의 후에 위치해야 MyBot 오류가 안 납니다.

# (이후 기존의 InfoModal, AgreementView, TradeStepView, EscrowView 코드를 그대로 붙여넣으세요)

if __name__ == "__main__":
    bot.run('여기에_토큰_입력')
