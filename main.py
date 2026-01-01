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

# --- [1. 설정 및 좌표] ---
# (사용자님의 기존 설정값 유지)
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 1455759161039261791
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 좌표 설정
SCAN_POINT = (773, 432)          
SCAN_RGB = (160, 179, 184)       
NICK_REGION = (773, 432, 250, 60) 

ACCEPT_BTN = (1048, 647)         
REJECT_BTN = (868, 648)          

CONFIRM_1ST_BTN = (1028, 687)    
CONFIRM_2ND_BTN = (1046, 685)    

# --- [클릭 보강 함수] ---
def force_click(coords):
    """마우스 이동 후 클릭이 씹히지 않도록 강제 클릭"""
    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
    pyautogui.mouseDown()
    time.sleep(0.1)
    pyautogui.mouseUp()

# --- [OCR 함수 유지] ---
def get_refined_nickname(region):
    screenshot = pyautogui.screenshot(region=region)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    custom_config = r'--oem 3 --psm 7'
    text = pytesseract.image_to_string(resized, config=custom_config, lang='eng')
    return "".join(filter(str.isalnum, text)).lower()

# --- [3. 자동화 핵심 로직 수정] ---
async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic and ":" in channel.topic else None
    
    status_embed = discord.Embed(title="접속 중", description="**비공개 서버에 접속하여 자동화를 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    webbrowser.open(ROBLOX_AMP_SERVER)
    await asyncio.sleep(20)
    
    status_embed.description = f"**봇 세팅 완료!**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇에게 거래를 걸어주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        while True:
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=25):
                detected_name = get_refined_nickname(NICK_REGION)
                print(f"🔍 판독된 이름: {detected_name}")

                if seller_nick.lower() in detected_name:
                    force_click(ACCEPT_BTN) # 1차 수락 버튼 클릭
                    break
                else:
                    if len(detected_name) > 2:
                        force_click(REJECT_BTN)
            await asyncio.sleep(0.5)

        # [수정] 1차 수락 후 창이 넘어갈 때까지 충분히 기다림 (3~5초)
        await asyncio.sleep(4) 
        
        # [수정] 아이템 확인용 스크린샷 (이제 1차 수락 후의 아이템 목록이 찍힘)
        pyautogui.screenshot("trade_check.png")
        
        verify_embed = discord.Embed(title="📦 아이템 확인", description=f"**판매자가 올린 아이템이 맞습니까?\n구매자(<@{buyer_id}>)님만 아래 버튼을 눌러주세요.**", color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=ItemVerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"**자동화 오류: {e}**", view=CallAdminOnlyView())

# --- [4. 수락 및 수령 확인 로직 수정] ---

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="아이템이 맞습니다", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        
        await interaction.response.send_message("**아이템 확인 완료. 최종 수락을 진행합니다.**")
        
        # 1. 1차 수락 좌표 클릭
        force_click(CONFIRM_1ST_BTN)
        print("✅ 1차 수락 클릭")
        
        # 2. 2차 수락 대기 (로블록스 쿨타임)
        await asyncio.sleep(6)
        
        # 3. 2차 최종 수락 클릭
        force_click(CONFIRM_2ND_BTN)
        print("✅ 2차 최종 수락 클릭")
        
        # 4. [수정] 실제로 아이템을 받았는지 확인 (거래창이 사라졌는지 체크)
        await asyncio.sleep(2)
        # SCAN_POINT의 색상이 더 이상 SCAN_RGB가 아니면 거래창이 닫힌 것(성공)으로 간주
        is_closed = not pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=25)
        
        if is_closed:
            final_embed = discord.Embed(title="수령 완료", description="**봇이 아이템을 안전하게 수령했습니다.\n판매자에게 송금을 진행해 주세요.**", color=0xffffff)
            await interaction.channel.send(embed=final_embed, view=TradeFinalControlView(self.buyer_id))
        else:
            await interaction.channel.send("**경고: 거래창이 아직 열려있습니다. 수락이 씹혔을 수 있으니 확인 바랍니다.**", view=CallAdminOnlyView())

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        force_click(REJECT_BTN)
        await interaction.response.send_message("**거래가 거절되었습니다.**", view=CallAdminOnlyView())

# (나머지 MyBot, EscrowView 등 기존 코드는 그대로 사용)
