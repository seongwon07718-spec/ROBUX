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

# --- [1. 좌표 설정: coords.txt 데이터 반영] ---
# 감지 및 클릭 좌표
SCAN_POINT = (773, 432)          # 유저 이름 표시 박스 시작점 (감지용)
SCAN_RGB = (160, 179, 184)       # 해당 좌표의 타겟 색상
NICK_REGION = (773, 432, 429, 51) # 유저 이름 박스 전체 영역 (1202-773, 483-432)

ACCEPT_BTN = (1048, 647)         # 거래 수락 버튼 중앙 (959~1137 사이)
REJECT_BTN = (868, 648)          # 거절 버튼 중앙 (779~957 사이)

CONFIRM_1ST = (1028, 687)        # 1차 수락 버튼 (965~1091 사이)
CONFIRM_2ND = (1046, 685)        # 2차 수락 버튼 (970~1122 사이)

# --- 기본 설정 ---
ADMIN_ROLE_ID = 1455824154283606195
ADMIN_LOG_CHANNEL_ID = 1455759161039261791
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- [2. 핵심 자동화 함수: 좌표+OCR 방식] ---

async def start_precision_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic and ":" in channel.topic else None
    
    # 1. 봇 세팅 안내 (20초 후 브섭 링크로 업데이트)
    status_embed = discord.Embed(title="접속중", description="**비공개 서버에 접속하여 자동화를 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)
    
    # 봇 실제 실행 (백그라운드)
    webbrowser.open(ROBLOX_AMP_SERVER)
    
    await asyncio.sleep(20) # 요청하신 20초 대기
    
    status_embed.description = f"**봇 세팅이 완료되었습니다.**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇({seller_nick})에게 거래를 걸어주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        # 2. 거래 감지 루프 (좌표 색상 감시)
        while True:
            # 지정한 좌표의 색상이 일치하는지 확인
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=10):
                # 닉네임 OCR 판독
                cap = pyautogui.screenshot(region=NICK_REGION)
                detected = pytesseract.image_to_string(cap).strip()
                
                if seller_nick.lower() in detected.lower():
                    pyautogui.click(ACCEPT_BTN) # 수락 클릭
                    break
                else:
                    pyautogui.click(REJECT_BTN) # 모르는 사람은 거절
            await asyncio.sleep(0.5)

        # 3. 아이템 검수 단계
        await asyncio.sleep(8) # 아이템 올리는 시간 대기
        pyautogui.screenshot("trade_check.png")
        
        verify_embed = discord.Embed(title="📦 아이템 검수 요청", 
                                     description=f"**판매자가 올린 아이템이 신청하신 내용과 맞습니까?**\n\n**구매자(<@{buyer_id}>)님만 아래 버튼을 눌러주세요.**", 
                                     color=0xffffff)
        verify_embed.set_image(url="attachment://trade_check.png")
        
        await channel.send(file=discord.File("trade_check.png"), embed=verify_embed, view=ItemVerifyView(buyer_id, seller_nick))

    except Exception as e:
        await channel.send(f"**자동화 오류 발생: {e}**", view=CallAdminOnlyView())

# --- [3. 버튼 인터페이스 클래스] ---

class ItemVerifyView(discord.ui.View):
    def __init__(self, buyer_id, seller_nick):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.seller_nick = seller_nick

    @discord.ui.button(label="아이템이 맞습니다", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id:
            return await interaction.response.send_message("구매자만 누를 수 있습니다.", ephemeral=True)
        
        await interaction.response.edit_message(content="**봇이 최종 수락을 진행합니다...**", view=None)
        
        # 1차 수락 좌표 클릭
        pyautogui.click(CONFIRM_1ST)
        await asyncio.sleep(5)
        # 2차 수락 좌표 클릭
        pyautogui.click(CONFIRM_2ND)
        
        success_embed = discord.Embed(title="수령 완료", description="**봇이 아이템을 안전하게 수령했습니다.**\n**이제 판매자에게 송금을 진행해 주세요.**", color=0xffffff)
        await interaction.channel.send(embed=success_embed, view=TradeFinalControlView(self.buyer_id))

    @discord.ui.button(label="아이템이 다릅니다", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer_id: return
        
        pyautogui.click(REJECT_BTN) # 인게임 거래 거절
        await interaction.response.send_message("**아이템 불일치로 거래가 취소되었습니다. 관리자를 호출하세요.**", view=CallAdminOnlyView())

# --- [기존 클래스 수정 연결] ---

class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id, seller_nick):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.seller_nick = seller_nick
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.gray, emoji="✅")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("거래 당사자만 가능합니다.", ephemeral=True)
        
        self.agreed_users.add(interaction.user.id)
        if len(self.agreed_users) >= 2:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            
            # 20초 대기 로직이 포함된 자동화 함수 실행
            asyncio.create_task(start_precision_automation(interaction, self.seller_nick))
        else:
            await interaction.response.send_message(f"**현재 동의 인원: ({len(self.agreed_users)}/2)**", ephemeral=True)

# (기존 TicketControlView, EscrowView, MyBot 클래스 등은 그대로 유지)
