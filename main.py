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
import random
import string
import requests
import numpy as np
from datetime import datetime
from discord import app_commands
from discord.ext import commands

# --- 설정 (기본 유지) ---
CATEGORY_ID = 1455820042368450580
ADMIN_ROLE_ID = 1455824154283606195
VERIFY_ROLE_ID = 1456531768109961287
ROBLOX_USER_SEARCH = "https://users.roblox.com/v1/users/search"
ROBLOX_USER_DETAIL = "https://users.roblox.com/v1/users/"
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커맨드 동기화 완료: {self.user.name}")

bot = MyBot()

# --- 인증 확인 및 역할 부여 뷰 ---
class VerifyCheckView(discord.ui.View):
    def __init__(self, roblox_name, roblox_id, target_key):
        super().__init__(timeout=None)
        self.roblox_name = roblox_name
        self.roblox_id = roblox_id
        self.target_key = target_key

        @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            res = requests.get(f"{ROBLOX_USER_DETAIL}{self.roblox_id}")
            if res.status_code == 200:
                about_text = res.json().get("description", "")
                if self.target_key in about_text:
                    role = interaction.guild.get_role(VERIFY_ROLE_ID)
                    await interaction.user.add_roles(role)

                    embed = discord.Embed(title="로블록스 - 인증완료", description=f"**{self.roblox_name}님의 인증이 완료되었습니다\n이제 다양한 서비스를 이용가능합니다**", color=0xffffff)
                    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
                    embed.set_image(url=img_url)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(f"**인증에 실패하였습니다\n로블 닉네임의 '소개'란에 인증 코드를 정확히 기재해주세요\n┗   `{self.target_key}`**", ephemeral=True)
            else:
                await interaction.response.send_message("**로블록스 API 요청에 실패하였습니다\n봇이 실시간으로 점검중이오니 잠시 후 시도해주세요**", ephemeral=True)

# --- 닉네임 이력 모달 ---
class NicknameModal(discord.ui.Modal, title="로블록스 닉네임 입력"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", placeholder="닉네임을 입력하세요", min_length=2)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        # 실시간 존재 여부 확인 API
        search = requests.get(ROBLOX_USER_SEARCH, params={"keyword": self.nickname.value, "limit": 1})
        data = search.json().get("data", [])

        if not data:
            self.original_view.roblox_user = None
            status_msg = "```❌ 존재하지 않는 이름입니다```"
            self.original_view.confirm_btn.disabled = True # 확인 버튼 잠금
        else:
            user = data[0]
            self.original_view.roblox_user = user
            status_msg = f"```{user['name']} (ID: {user['id']})```"
            self.original_view.confirm_btn.disabled = False # 확인 버튼 활성화

        # 임베드 업데이트
        new_embed = discord.Embed(color=0xffffff)
        new_embed.add_field(name="로블록스 닉네임", value=status_msg)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png"
        new_embed.set_image(url=img_url)
        
        await interaction.response.edit_message(embed=new_embed, view=VerifyStepView(), ephemeral=True)

# 2. 정보 수정 및 완료 버튼이 있는 임베드 뷰
class VerifyStepView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roblox_user = None

    @discord.ui.button(label="정보 수정하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="quick", id=1455996651218141286))
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal(self))

    @discord.ui.button(label="진행하기", style=discord.ButtonStyle.green, disabled=True, emoji=discord.PartialEmoji(name="ID", id=1455996414684303471)) # 초기엔 잠금
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 랜덤 문구 생성 및 최종 단계 진행
        verify_key = "FLIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        embed = discord.Embed(title="최종 단계 - 프로필 확인", color=discord.Color.gold())
        embed.description = (
            f"**로블록스 계정 = ** {self.roblox_user['name']}\n"
            f"**인증 문구 = ** `{verify_key}`\n\n"
            f"**┗   로블록스 프로필 소개 칸에 위 문구를 작성하고 아래 버튼을 눌러주세요**"
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png"
        embed.set_image(url=img_url)
        # 여기서부터는 이전과 동일한 VerifyCheckView(최종 확인 뷰) 호출
        await interaction.response.edit_message(embed=embed, view=VerifyCheckView(self.roblox_user['name'], self.roblox_user['id'], verify_key), ephemeral=True)

# --- 티켓 제어 및 초기 뷰 ---
class TwicketControlView(discord.ui.View):
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
        await interaction.response.edit_message(view=self)
        embed = discord.Embed(title="거래 정보 확인", description="**거래 정보 수정 버튼을 눌러 로블 닉네임을 적어주세요\n두 분 모두 '계속진행'을 눌러야 다음 단계로 이동합니다**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456321236643741728/IMG_0751.png"
        embed.set_image(url=img_url)
        await interaction.followup.send(embed=embed)

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="충전문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="start_escrow", emoji=discord.PartialEmoji(name="enable", id=1455996417335365643))
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        verify_role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if verify_role not in interaction.user.roles:
            await interaction.response.send_message("**인증된 사용자만 티켓을 열 수 있습니다**", ephemeral=True)
            return
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"충전-{user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"**{ticket_channel.mention} 채널이 생성되었습니다**", ephemeral=True)
        embed1 = discord.Embed(title="충전 안내", description=f"**티켓 생성자 = {user.mention}\n10분동안 충전 미진행시 자동으로 채널 삭제됩니다**", color=0xffffff)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
        embed1.set_image(url=img_url)
    
        view = TwicketControlView(owner_id=user.id)
        await ticket_channel.send(content=f"@everyone", embed=embed1, view=view)

@bot.tree.command(name="game", description="로블록스 전용 플립 패널")
async def escrow_panel(interaction: discord.Interaction):
    # 1. 명령어 입력자에게만 보이는 완료 문구 전송
    await interaction.response.send_message("**DONE**", ephemeral=True)

    # 2. 실제 채널에 전송될 패널 임베드 설정
    embed = discord.Embed(
        title="로블록스 - GAME BOT", 
        description=(
            "**아이템을 베팅하여 아이템을 불려보세요**\n"
            "**아래 버튼을 눌려 충전진행 하시면됩니다**\n\n"
            "**┗   티켓 여시면 중개봇이 안내해줍니다**\n"
            "**┗   상호작용 오류시 문의부탁드려요**\n\n"
            "**[게임 이용약관](https://swnx.shop)         [디스코드 TOS](https://discord.com/terms)**"
        ), 
        color=0xffffff
    )

    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
    embed.set_image(url=img_url)

    # 3. interaction.channel.send를 사용하여 실제 패널 전송
    await interaction.channel.send(embed=embed, view=EscrowView())

@bot.tree.command(name="verify", description="로블록스 인증하기 패널")
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("**DONE**", ephemeral=True)

    embed = discord.Embed(
        title="로블록스 - VERIFY BOT", 
        description=(
            "**게임을 이용하실려면 인증은 필수입니다**\n"
            "**아래 버튼을 눌러 인증 절차를 시작하세요**\n\n"
            "**┗   인증 후 게임 이용이 가능합니다**\n"
            "**┗   상호작용 오류시 문의부탁드려요**\n\n"
            "**[로블록스 이용약관](https://www.roblox.com/terms)         [디스코드 TOS](https://discord.com/terms)**"
        ), 
        color=0xffffff
    )

    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1456494848457572433/IMG_0753.png"
    embed.set_image(url=img_url)

    await interaction.channel.send(embed=embed, view=VerifyCheckView())

if __name__ == "__main__":
    bot.run('')
