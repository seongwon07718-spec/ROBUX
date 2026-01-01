import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
import pytesseract
import os
from datetime import datetime
from discord import app_commands
from discord.ext import commands

# --- 설정 (기존 유지) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 123456789012345678 # 대화내용이 저장될 관리자 채널 ID 입력 필수
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"
IMG_PATH = "images/"

# Tesseract OCR 경로 설정 (제공해주신 이미지 경로 반영)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- 이미지 감지 보조 함수 ---
def get_img(name): return f"{IMG_PATH}{name}"

async def click_img(img_name, conf=0.8, retry=10):
    for _ in range(retry):
        loc = pyautogui.locateCenterOnScreen(get_img(img_name), confidence=conf)
        if loc:
            pyautogui.click(loc)
            return True
        await asyncio.sleep(0.5)
    return False

# --- 대화 로그 저장 및 삭제 함수 ---
async def save_log_and_close(channel):
    messages = [f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author.name}: {m.content}" async for m in channel.history(limit=None, oldest_first=True)]
    filename = f"log_{channel.name}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(messages))
    
    log_ch = channel.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
    if log_ch:
        await log_ch.send(content=f"📑 **중개 완료 로그** | {channel.name}", file=discord.File(filename))
    
    os.remove(filename)
    await channel.send(embed=discord.Embed(description="✅ **중개가 완료되었습니다. 5분 후 채널이 삭제됩니다.**", color=0x00ff00))
    await asyncio.sleep(300)
    await channel.delete()

# --- [핵심] 로블록스 자동화 접속 및 거래 수령 함수 ---
async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic else None
    
    status_embed = discord.Embed(title="접속중", description="**비공개 서버에 접속하여 자동화를 세팅 중입니다.**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    try:
        # 1. 게임 실행 및 입장
        webbrowser.open(ROBLOX_AMP_SERVER)
        await asyncio.sleep(5); pyautogui.press('enter')
        await asyncio.sleep(35) # 로딩 대기

        # 2. 초기 팝업 정리 및 플레이 (play_button, close_button)
        await click_img("play_button.png")
        await asyncio.sleep(3)
        for _ in range(3): await click_img("close_button.png", retry=2)

        # 3. 거래 장소 이동 (backpack_icon -> gifts_tab -> plus_icon -> yes_button)
        await click_img("backpack_icon.png")
        await click_img("gifts_tab.png")
        await click_img("plus_icon.png")
        await click_img("yes_button.png") # 선물 상점으로 이동

        status_embed.title = "거래 대기"
        status_embed.description = f"**봇이 선물 상점에 도착했습니다.**\n**[{seller_nick}]** 님의 거래 요청을 기다리는 중입니다.\n(다른 유저의 요청은 자동으로 거절됩니다.)"
        await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

        # 4. OCR 선별 수락 (trade_popup_area, accept_request, reject_other)
        while True:
            popup = pyautogui.locateOnScreen(get_img('trade_popup_area.png'), confidence=0.7)
            if popup:
                x, y, w, h = popup
                nick_capture = pyautogui.screenshot(region=(x + 70, y + 30, 200, 50))
                detected_text = pytesseract.image_to_string(nick_capture).strip()
                
                if seller_nick.lower() in detected_text.lower():
                    await click_img("accept_request.png")
                    break
                else:
                    await click_img("reject_other.png")
            await asyncio.sleep(1)

        # 5. 아이템 검수 (trade_verify 스크린샷 전송)
        await asyncio.sleep(10) # 아이템 올리는 시간 대기
        pyautogui.screenshot("trade_check.png")
        verify_embed = discord.Embed(title="📦 아이템 확인 요청", description=f"판매자가 올린 아이템이 맞습니까?\n구매자(<@{buyer_id}>)님만 버튼을 눌러주세요.", color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=ItemVerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"❌ 자동화 중 오류 발생: {e}", view=CallAdminOnlyView())

# --- 인터페이스 뷰 클래스들 ---

class CallAdminOnlyView(discord.ui.View):
    @discord.ui.button(label="관리자 호출", style=discord.ButtonStyle.danger, emoji="🆘")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"<@&{ADMIN_ROLE_ID}> 관리자 호출 접수!")
        await interaction.response.send_message("관리자를 호출했습니다.", ephemeral=True)

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="예, 구매 아이템이 맞습니다", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        # 봇이 게임 내 거래 최종 수락 (confirm_trade -> final_accept)
        await click_img("confirm_trade.png")
        await asyncio.sleep(5)
        await click_img("final_accept.png")
        
        embed = discord.Embed(title="💰 송금 단계", description="**봇이 아이템 수령을 완료했습니다.**\n이제 판매자에게 대금을 송금해 주세요.", color=0xffffff)
        await interaction.response.edit_message(embed=embed, view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아니요, 아이템이 다릅니다", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        # 거절 및 반환 로직 (필요 시 작성)
        await interaction.response.send_message("❌ 아이템 불일치로 거래가 중단되었습니다. 관리자를 호출하세요.", view=CallAdminOnlyView())

class TradeFinalControlView(discord.ui.View):
    def __init__(self, buyer_id):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id

    @discord.ui.button(label="거래완료", style=discord.ButtonStyle.success)
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 성공 로그 저장 및 종료
        await interaction.response.send_message("🎊 모든 거래가 완료되었습니다! 5분 뒤 티켓이 닫힙니다.")
        asyncio.create_task(save_log_and_close(interaction.channel))

    @discord.ui.button(label="거래거파", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚫 거래가 거파되었습니다. 판매자에게 아이템을 돌려줍니다.", view=CallAdminOnlyView())

    @discord.ui.button(label="관리자 호출", style=discord.ButtonStyle.secondary, emoji="🆘")
    async def admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(f"<@&{ADMIN_ROLE_ID}> 관리자 호출 접수!")

# --- [MyBot 및 나머지 코드는 기존 그대로 사용] ---
# (이 아래에 본인의 MyBot 클래스와 EscrowView 등을 그대로 붙여넣으시면 됩니다)
