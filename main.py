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
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 1455759161039261791
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 좌표 설정 (본인의 환경에 맞게 coords.txt 수치로 수정 필수)
SCAN_POINT = (773, 432)          # 거래창 감지용 좌표
SCAN_RGB = (160, 179, 184)       # 거래창 감지용 색상
NICK_REGION = (773, 432, 250, 60) # 닉네임 영역

ACCEPT_BTN = (1048, 647)         # 거래 요청 '수락' 버튼
REJECT_BTN = (868, 648)          # 거래 요청 '거절' 버튼

CONFIRM_1ST_BTN = (1028, 687)    # 1차 수락 버튼 좌표
CONFIRM_2ND_BTN = (1046, 685)    # 2차 최종 수락 버튼 좌표

# --- [2. 강화된 OCR 판독 함수] ---
def get_refined_nickname(region):
    """이미지 전처리를 통해 판독률을 극대화 (흑백 전환 + 확대)"""
    screenshot = pyautogui.screenshot(region=region)
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 임계값 처리로 글자를 더 선명하게 만듦
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    # 2배 확대
    resized = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    custom_config = r'--oem 3 --psm 7'
    text = pytesseract.image_to_string(resized, config=custom_config, lang='eng')
    return "".join(filter(str.isalnum, text)).lower()

# --- [3. 자동화 핵심 함수] ---
async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic and ":" in channel.topic else None
    
    # 1. 초기 임베드 (접속 중)
    status_embed = discord.Embed(title="접속 중", description="**비공개 서버에 접속하여 자동화를 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    webbrowser.open(ROBLOX_AMP_SERVER)
    
    # 2. 20초 대기 후 임베드 수정
    await asyncio.sleep(20)
    status_embed.description = f"**봇 세팅 완료!**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇에게 거래를 걸어주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        # 3. 거래 감지 및 닉네임 확인 루프
        while True:
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=25):
                detected_name = get_refined_nickname(NICK_REGION)
                print(f"🔍 판독된 이름: {detected_name}")

                if seller_nick.lower() in detected_name:
                    pyautogui.click(ACCEPT_BTN)
                    break
                else:
                    if len(detected_name) > 2: # 엉뚱한 사람이면 거절
                        pyautogui.click(REJECT_BTN)
            await asyncio.sleep(0.5)

        # 4. 아이템 검수 스크린샷 전송
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
        
        # 버튼 클릭 후 즉시 게임 좌표 클릭 실행
        await interaction.response.send_message("**구매자 확인 완료. 봇이 게임 내에서 수락을 진행합니다.**")
        
        # 1차 수락 좌표 클릭 (상대방 상관없이 즉시 클릭)
        pyautogui.click(CONFIRM_1ST_BTN)
        print("✅ 1차 수락 좌표 클릭 완료")
        
        # 2차 수락 대기 (로블록스 시스템상 대기 시간 필요)
        await asyncio.sleep(5)
        
        # 2차 최종 수락 좌표 클릭
        pyautogui.click(CONFIRM_2ND_BTN)
        print("✅ 2차 최종 수락 좌표 클릭 완료")
        
        final_embed = discord.Embed(title="수령 완료", description="**봇이 아이템을 안전하게 받았습니다.\n판매자에게 송금을 진행해 주세요.**", color=0xffffff)
        await interaction.channel.send(embed=final_embed, view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        pyautogui.click(REJECT_BTN)
        await interaction.response.send_message("**거래가 중단되었습니다. 관리자를 호출하세요.**", view=CallAdminOnlyView())

# --- [이후 기존 클래스/함수들은 건들지 않고 그대로 유지] ---
# (TradeFinalControlView, AgreementView, MyBot, TicketControlView 등...)
