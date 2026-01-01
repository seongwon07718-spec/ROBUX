import discord
import asyncio
import aiohttp 
import re 
import webbrowser
import pyautogui
import time
import pytesseract
import os
import cv2  # 이미지 처리를 위해 필수 추가
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

# 좌표 설정
SCAN_POINT = (773, 432)          
SCAN_RGB = (160, 179, 184)       
NICK_REGION = (773, 432, 250, 60) 

ACCEPT_BTN = (1048, 647)         
REJECT_BTN = (868, 648)          

CONFIRM_1ST_BTN = (1028, 687)    
CONFIRM_2ND_BTN = (1046, 685)    

# --- [2. 강화된 OCR 판독 함수] ---
def get_refined_nickname(region):
    """이미지 전처리를 통해 판독률을 극대화 (흑백 전환 + 확대)"""
    screenshot = pyautogui.screenshot(region=region)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 임계값 처리로 글자를 더 선명하게 만듦 (검은 배경 흰 글자 추출)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    # 2배 확대 (OCR 인식률 대폭 향상)
    resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    custom_config = r'--oem 3 --psm 7'
    text = pytesseract.image_to_string(resized, config=custom_config, lang='eng')
    return "".join(filter(str.isalnum, text)).lower()

# --- [3. 자동화 핵심 함수] ---
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
                # 전처리된 OCR 함수 사용
                detected_name = get_refined_nickname(NICK_REGION)
                print(f"🔍 판독된 이름: {detected_name}")

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
        await channel.send(f"**자동화 오류: {e}**", view=CallAdminOnlyView())

# --- [4. 인터페이스 및 버튼 수락 로직] ---

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="아이템이 맞습니다", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        
        await interaction.response.send_message("**구매자 확인 완료. 봇이 게임 내에서 수락을 진행합니다.**")
        
        # 1차 수락 즉시 클릭 (상대방 무관)
        pyautogui.click(CONFIRM_1ST_BTN)
        print("✅ 1차 수락 좌표 클릭 완료")
        
        # 2차 수락을 위한 대기 (게임 시스템상 시간차 필요)
        await asyncio.sleep(5)
        
        # 2차 최종 수락 즉시 클릭
        pyautogui.click(CONFIRM_2ND_BTN)
        print("✅ 2차 최종 수락 좌표 클릭 완료")
        
        final_embed = discord.Embed(title="수령 완료", description="**봇이 아이템을 안전하게 받았습니다.\n판매자에게 송금을 진행해 주세요.**", color=0xffffff)
        await interaction.channel.send(embed=final_embed, view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        pyautogui.click(REJECT_BTN)
        await interaction.response.send_message("**거래가 중단되었습니다. 관리자를 호출하세요.**", view=CallAdminOnlyView())

# --- [기존 클래스 및 로직 유지] ---
# (TradeFinalControlView, MyBot, InfoModal, AgreementView, TradeStepView, TicketControlView, EscrowView 등 기존 코드 그대로 삽입)
# ... (생략된 기존 코드는 사용자가 작성한 내용을 그대로 사용하시면 됩니다) ...

if __name__ == "__main__":
    # 토큰을 넣어 실행하세요
    bot.run('YOUR_TOKEN')
