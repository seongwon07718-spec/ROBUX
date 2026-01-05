import discord
import asyncio
import random
import string
import aiohttp
import re
import numpy as np
import os
import time
import json
from fastapi import FastAPI, Request
app = FastAPI()

import uvicorn
from PIL import Image, ImageDraw, ImageFont
import uuid
import io
import threading
from discord.ext import tasks
from datetime import datetime
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
from database import load_db, save_verified_user, save_bet_info

CATEGORY_ID = 1449190712162910409
ADMIN_ROLE_ID = 1449194995507662858
VERIFY_ROLE_ID = 1456858132163854521

CHANGE_WEBHOOK_URL = "https://discord.com/api/webhooks/1456622457074094194/ZDNAr66dolnWETs7SaOzrhzq_TTg06MaKf-WzA_nBarAwU1tDA7UHsOrkRZi2co4zWp7"

ROBLOX_MM2_SERVER = "https://www.roblox.com/share?code=5f4d3c2b1a0987654321fedcba987654&type=Server"
ROBLOX_AMP_SERVER = "https://www.roblox.com/share?code=6d6c2a317d55d640a6c3fe4db56e6728&type=Server"

VERIFIED_USERS_FILE = "verified_users.json"
RECHARGE_LOG_FILE = "recharge_logs.json"

BOT_DATA = {
    "머더": [
        {"name": "Der_FlipBot", "id": "10270924697", "link": "https://www.roblox.com/share?code=25b822f338e993409b09a97be7154524&type=Server"}
    ],
    "입양": [
        {"name": "Der_AmpBot", "id": "10276328742", "link": "https://www.roblox.com/share?code=debbcc7094e1a04e9e63347e6bd6c34e&type=Server"}
    ]
}

status_message = None

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"커멘드 DONE {self.user.name}")

bot = MyBot()

def get_roblox_id(discord_id):
    try:
        with open('verified_users.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(discord_id))
    except: return None

async def get_roblox_thumb(roblox_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_id}&size=150x150&format=Png&isCircular=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data['data'][0]['imageUrl'] if data['data'] else None
    return "https://tr.rbxcdn.com/38c6dec17b8764831362e59a68688439/420/420/Image/Png"

async def create_merged_gif(result_side, c_data, p_data, bet_id):
    base_gif_path = f"final_fix_{result_side}.gif"
    if not os.path.exists(base_gif_path): return None

    async with aiohttp.ClientSession() as session:
        async with session.get(c_data['thumb']) as r1, session.get(p_data['thumb']) as r2:
            c_img = Image.open(io.BytesIO(await r1.read())).convert("RGBA").resize((120, 120))
            p_img = Image.open(io.BytesIO(await r2.read())).convert("RGBA").resize((120, 120))

    base_gif = Image.open(base_gif_path)
    frames = []
    # 폰트 경로는 본인 서버 환경에 맞춰 수정 (예: 나눔고딕, arial 등)
    try: font = ImageFont.truetype("arial.ttf", 20)
    except: font = ImageFont.load_default()

    for frame in range(base_gif.n_frames):
        base_gif.seek(frame)
        # 프레임 복사 및 드로잉 준비
        canvas = base_gif.convert("RGBA")
        draw = ImageDraw.Draw(canvas)

        # 1. 왼쪽: 생성자 프사 + 이름
        canvas.paste(c_img, (40, canvas.height // 2 - 60), c_img)
        draw.text((40, canvas.height // 2 + 70), c_data['name'], fill="white", font=font)

        # 2. 오른쪽: 참가자 프사 + 이름
        canvas.paste(p_img, (canvas.width - 160, canvas.height // 2 - 60), p_img)
        draw.text((canvas.width - 160, canvas.height // 2 + 70), p_data['name'], fill="white", font=font)

        # 3. 하단: 고유 ID
        draw.text((canvas.width // 2 - 60, canvas.height - 35), f"ID: #{bet_id[:10]}", fill=(200, 200, 200), font=font)

        frames.append(canvas)

    output_path = f"temp_{bet_id}.gif"
    frames[0].save(output_path, save_all=True, append_images=frames[1:], 
                   duration=base_gif.info.get('duration', 20), loop=0, optimize=True)
    return output_path

def get_user_data(roblox_id):
    try:
        with open(VERIFIED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get(str(roblox_id))
    except Exception: return None

def log_transaction(action, discord_id, roblox_name, items):
    try:
        with open(RECHARGE_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except: logs = []
    
    logs.append({
        "action": action,
        "discord_id": discord_id,
        "roblox_name": roblox_name,
        "items": items,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    with open(RECHARGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

async def check_roblox_user(username: str):
    if not re.match(r"^[A-Za-z0-9_]{3,}$", username):
        return None, "형식 불일치 (영어/숫자/언더바 3자 이상)"
    url = "https://users.roblox.com/v1/usernames/users"
    data = {"usernames": [username], "excludeBannedUsers": True}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                res_json = await resp.json()
                if res_json.get("data"):
                    return res_json["data"][0]["name"], "존재함"
                else:
                    return None, "존재하지 않는 닉네임"
            else:
                return None, "API 오류"
            
async def get_bot_status(roblox_id):
    """로블록스 API로 봇의 실시간 접속 여부 확인"""
    url = "https://presence.roblox.com/v1/presence/users"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"userIds": [int(roblox_id)]}) as resp:
            data = await resp.json()
            if data and "userPresences" in data:
                return data["userPresences"][0].get("userPresenceType") in [2, 3]
    return False

class BotStatusSelect(discord.ui.Select):
    def __init__(self, category, options):
        super().__init__(placeholder=f"{category} 전용 봇을 선택하세요", options=options)
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        selected_name = self.values[0]
        bot_list = BOT_DATA.get(self.category, [])
        target = next((b for b in bot_list if b["name"] in selected_name), None)
        
        if target:
            embed = discord.Embed(title="BloxFlip - 서버접속", color=0xffffff)
            embed.description = f"**봇 이름ㅣ{target['name']}\n\n╰ 봇 사칭 주의하세요\n╰ 사칭한테 사기당할 시 책임X\n╰ 닉네임 꼭 확인하고 거래하세요\n\n서버링크ㅣ[여기를 클릭하여 입장하기]({target['link']})**"
            await interaction.response.send_message(embed=embed, ephemeral=True)

class BotSelectView(discord.ui.View):
    def __init__(self, category, dropdown_options):
        super().__init__(timeout=60)
        self.add_item(BotStatusSelect(category, dropdown_options))

class VerifyStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="로블록스 인증하기", style=discord.ButtonStyle.gray,
                       emoji=discord.PartialEmoji(name="verified", id=1455996645337468928))
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="BloxFlip - 인증 절차",
            description="**╰ 아래 정보수정 버튼으로 로블록스 닉네임 입력해주세요\n╰ 아래에 닉네임을 입력하고 진행 버튼을 눌러주세요**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        embed.set_image(url=img_url)
        await interaction.response.send_message(embed=embed, view=VerifyStepView(), ephemeral=True)

class NicknameModal(discord.ui.Modal, title="로블록스 닉네임 입력"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", min_length=3)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        username = self.nickname.value.strip()
        name, status = await check_roblox_user(username)
        if name is None:
            self.original_view.roblox_user = None
            status_msg = f"```{status}```"
            self.original_view.confirm_btn.disabled = True
        else:
            self.original_view.roblox_user = {"name": name}
            status_msg = f"```{name}```"
            self.original_view.confirm_btn.disabled = False

        embed = discord.Embed(color=0xffffff)
        embed.title = "BloxFlip - 로블록스 닉네임 확인"
        embed.description = "**╰ 아래 입력한 닉네임이 맞는지 확인해주세요\n╰ 맞다면 진행하기 버튼을 눌러주세요**"
        embed.add_field(name="로블록스 닉네임", value=status_msg)
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        embed.set_image(url=img_url)
        await interaction.response.edit_message(embed=embed, view=self.original_view)

class VerifyStepView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.roblox_user = None

    @discord.ui.button(label="정보 수정하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="quick", id=1455996651218141286))
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NicknameModal(self))

    @discord.ui.button(label="진행하기", style=discord.ButtonStyle.green, disabled=True, emoji=discord.PartialEmoji(name="ID", id=1455996414684303471))
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        verify_key = "FLIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        embed = discord.Embed(
            title="BloxFlip - 프로필 확인",
            description=(
                f"**╰ 로블록스 계정 ㅣ {self.roblox_user['name']}**\n"
                f"**╰ 인증 문구 ㅣ `{verify_key}`**\n\n"
                "**╰ 로블록스 프로필 소개란에 위 문구를 반드시 작성해주세요**"
            ),
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        embed.set_image(url=img_url)
        await interaction.response.edit_message(embed=embed, view=VerifyCheckView(self.roblox_user['name'], verify_key))

class VerifyCheckView(discord.ui.View):
    def __init__(self, roblox_name, verify_key):
        super().__init__(timeout=None)
        self.roblox_name = roblox_name
        self.verify_key = verify_key

    @discord.ui.button(label="프로필 수정 완료", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="check_box_90", id=1455996410070700225))
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

            button.disabled = True
            button.label = "봇이 프로필을 확인했습니다"
            button.style = discord.ButtonStyle.green

            view = self
            await interaction.edit_original_response(view=view)

        search_url = "https://users.roblox.com/v1/usernames/users"
        search_data = {"usernames": [self.roblox_name], "excludeBannedUsers": True}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(search_url, json=search_data) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if not res_json.get("data"):
                        return await interaction.response.send_message("**로블록스 유저 정보를 찾을 수 없습니다**", ephemeral=True)
                    
                    user_id = res_json["data"][0]["id"]
                    
                    detail_url = f"https://users.roblox.com/v1/users/{user_id}"
                    async with session.get(detail_url) as detail_resp:
                        if detail_resp.status == 200:
                            detail_data = await detail_resp.json()
                            description = detail_data.get("description", "")
                            
                            if self.verify_key in description:
                                role = interaction.guild.get_role(VERIFY_ROLE_ID)
                                if role:
                                    await interaction.user.add_roles(role)

                                    await save_verified_user(interaction.user.id, interaction.user.name, self.roblox_name)

                                    await send_verify_webhook(interaction.user, self.roblox_name)

                                    embed = discord.Embed(
                                        title="BloxFlip - 인증 완료",
                                        description=f"**╰ {self.roblox_name}님, 인증이 완료되었습니다\n╰ 이제 모든 기능을 이용하실 수 있습니다**",
                                        color=0xffffff
                                    )
                                    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
                                    embed.set_image(url=img_url)

                                    await interaction.followup.send(embed=embed, ephemeral=True)
                                else:
                                    await interaction.response.send_message("**서버에 설정된 인증 역할 ID가 올바르지 않습니다\n관리자에게 문의하세요**", ephemeral=True)
                            else:
                                await interaction.response.send_message(
                                    f"**╰ 인증 문구를 찾을 수 없습니다\n╰ 작성해야 할 문구 ㅣ `{self.verify_key}`\n╰ 프로필 소개란을 다시 확인해주세요**", 
                                    ephemeral=True
                                )
                        else:
                            await interaction.response.send_message("**로블록스 상세 정보를 불러오는 중 오류가 발생했습니다**", ephemeral=True)
                else:
                    await interaction.response.send_message("**로블록스 서버와 통신 중 오류가 발생했습니다**", ephemeral=True)

async def send_verify_webhook(user, roblox_name):
    WEBHOOK_URL = "https://discord.com/api/webhooks/1456622453534101616/VUgI2N21lMqhITVXWO5ypF76bQPnIpLSNV28qYSU998zmC7nHONvYg8l--oxDVRheI72"
    
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            
        embed = discord.Embed(
            title="BloxFlip - 인증 유저",
            description=f"[{roblox_name}](https://www.roblox.com/users/profile?username={roblox_name})\n**새로운 로블록스 유저가 인증했습니다**",
            color=0xffffff
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="디스코드", value=f"```{user.mention} ({user.name})```", inline=True)
        embed.add_field(name="로블록스", value=f"```{roblox_name}```", inline=True)
        embed.add_field(name="인증 시간", value=f"<t:{int(time.time())}:F>", inline=False)

        await webhook.send(embed=embed, username="BloxFlip - 인증로그")

class VerifyInfoView(discord.ui.View):
    def __init__(self, data, per_page=10):
        super().__init__(timeout=None)
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(data) - 1) // per_page + 1 if data else 1

    def make_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_data = self.data[start:end]

        embed = discord.Embed(
            title="BloxFlip - 인증된 유저 목록",
            description=f"```총 인증 인원 = {len(self.data)}명```",
            color=0xffffff
        )

        if not page_data:
            embed.add_field(name="유저 정보", value="**인증된 유저가 없습니다**")
        else:
            list_text = ""
            for i, user in enumerate(page_data, start=start + 1):
                list_text += f"{i}. {user['discord_name']} | {user['roblox_name']}\n"
            embed.add_field(name=f"유저 정보", value=list_text)
        return embed

class EscrowDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="머더 미스터리", description="머더 미스터리 충전 안내를 진행합니다", emoji=discord.PartialEmoji(name="subdirectory", id=1455996649900998830), value="머더"),
            discord.SelectOption(label="입양하세요", description="입양하세요 충전 안내를 진행합니다", emoji=discord.PartialEmoji(name="subdirectory", id=1455996649900998830), value="입양"),
        ]
        super().__init__(placeholder="충전할 로블록스 게임을 선택해주세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        game_choice = self.values[0]
        await interaction.response.defer(ephemeral=True)

        bot_options = []
        for bot in BOT_DATA.get(game_choice, []):
            is_online = await get_bot_status(bot["id"])
            status_emoji = "🟢" if is_online else "🔴"
            status_txt = "온라인" if is_online else "오프라인"
            
            bot_options.append(discord.SelectOption(
                label=f"{bot['name']}",
                emoji=status_emoji,
                description=f"현재 {status_txt} 상태입니다",
                value=bot['name']
            ))

        if not bot_options:
            return await interaction.followup.send("**현재 선택 가능한 봇이 없습니다**", ephemeral=True)

        embed = discord.Embed(
            title="BloxFlip - 충전하기",
            description=f"**╰ 아래 드롭바를 눌려 충전 진행하세요**\n**╰ 현재 {game_choice} 게임의 충전 가능한 봇 목록입니다**",
            color=0xffffff
        )

        bot_view = discord.ui.View()
        bot_view.add_item(BotStatusSelect(game_choice, bot_options))
        await interaction.followup.send(embed=embed, view=bot_view, ephemeral=True)

class EscrowView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(EscrowDropdown())

class ResultShowView(discord.ui.View):
    def init(self, bet_id, c_data, p_data, result): # 4개의 인자를 받음
        super().init(timeout=None)
        self.bet_id = bet_id
        self.c = c_data
        self.p = p_data
        self.result = result

    @discord.ui.button(label="VIEW", style=discord.ButtonStyle.success)
    async def view_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.c['id'], self.p['id']]:
            return await interaction.response.send_message("참여자 전용입니다.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        final_gif_path = await create_merged_gif(self.result, self.c, self.p, self.bet_id)
        
        file = discord.File(final_gif_path, filename="result.gif")
        embed = discord.Embed(color=0xffffff)
        embed.set_image(url="attachment://result.gif")
        
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        if os.path.exists(final_gif_path): os.remove(final_gif_path)

# --- 베팅 대기 뷰 ---
class BettingProcessView(discord.ui.View):
    def __init__(self, creator, side, res):
        super().__init__(timeout=None)
        self.creator, self.side, self.res = creator, side, res

    @discord.ui.button(label="JOIN", style=discord.ButtonStyle.primary)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.creator.id:
            return await interaction.response.send_message("본인 게임 불가", ephemeral=True)
        
        bet_id = str(uuid.uuid4()).replace("-", "").upper()
        c_rid, p_rid = get_roblox_id(self.creator.id), get_roblox_id(interaction.user.id)
        c_thumb, p_thumb = await get_roblox_thumb(c_rid), await get_roblox_thumb(p_rid)
        
        c_data = {'id': self.creator.id, 'name': self.creator.display_name, 'thumb': c_thumb, 'side': self.side}
        p_data = {'id': interaction.user.id, 'name': interaction.user.display_name, 'thumb': p_thumb, 'side': 'T' if self.side == 'H' else 'H'}
        
        save_bet_info(bet_id, self.creator.id, interaction.user.id, self.res)
        
        await interaction.message.edit(view=ResultShowView(bet_id, c_data, p_data, self.res))
        await interaction.response.send_message("참가 완료! VIEW 버튼을 누르세요.", ephemeral=True)

class CoinChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_choice(self, interaction: discord.Interaction, user_side: str):
        result_side = random.choice(["H", "T"])
        is_win = (user_side == result_side)

        wait_embed = discord.Embed(
            title="BloxFlip - 베팅완료",
            description=f"**╰ {interaction.user.mention}님이 **{user_side}**에 베팅하셨습니다**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        wait_embed.set_image(url=img_url)
        view = ResultShowView(result_side, is_win)
        await interaction.response.edit_message(embed=wait_embed, view=view)

    @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji(name="emoji_23", id=1457645330240634880))
    async def head_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "H")

    @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="emoji_22", id=1457645454887096425))
    async def tail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "T")

class BotStateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

@tasks.loop(seconds=600)
async def bot_status_loop():
    global status_msg
    if status_msg:
        try:
            new_embed = await create_bot_state_embed()
            await status_msg.edit(embed=new_embed)
        except Exception as e:
            print(f"자동 업데이트 중 오류 발생: {e}")
            bot_status_loop.stop()

async def create_bot_state_embed():
    embed = discord.Embed(
        title="BloxFlip - 봇 상태",
        description=f"**╰ 봇 상태를 실시간으로 확인하세요**\n**╰ 10분마다 갱신됩니다**",
        color=0xffffff
    )
    
    for category, bots in BOT_DATA.items():
        status_lines = []
        for bot in bots:
            is_online = await get_bot_status(bot["id"])
            emoji = "🟢 온라인" if is_online else "🔴 오프라인"
            status_lines.append(f"```{bot['name']}ㅣ{emoji}```")
        
        embed.add_field(
            name=f"{category}",
            value="\n".join(status_lines) if status_lines else "```등록된 봇 없음```",
            inline=False
        )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)
    return embed

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="티켓닫기", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji=discord.PartialEmoji(name="close", id=1455996415976407102))
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**티켓이 5초 후에 삭제됩니다**", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="문의 티켓열기", style=discord.ButtonStyle.gray, custom_id="open_ticket", emoji=discord.PartialEmoji(name="enable", id=1455996417335365643))
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        category = guild.get_channel(CATEGORY_ID)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_role(ADMIN_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel_name = f"문의-{user.name}"
        
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message(f"**이미 생성된 티켓이 있습니다 {existing_channel.mention}**", ephemeral=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"**{ticket_channel.mention} 티켓이 생성되었습니다**", ephemeral=True)

        embed = discord.Embed(
            title="BloxFlip - 문의티켓",
            description=f"**{user.mention}님, 무엇을 도와드릴까요?\n관리자가 확인하기 전까지 내용을 미리 남겨주세요\n\n티켓을 닫으려면 아래 **티켓 닫기** 버튼을 눌러주세요**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        embed.set_image(url=img_url)
        await ticket_channel.send(content=f"{user.mention} @everyone", embed=embed, view=TicketControlView())

@bot.tree.command(name="충전패널", description="로블록스 충전하기 패널")
@app_commands.checks.has_permissions(administrator=True)
async def escrow_panel(interaction: discord.Interaction):
    await interaction.response.send_message("**DONE**", ephemeral=True)

    embed = discord.Embed(
        title="BloxFlip - 충전하기", 
        description=(
            "**╰ 충전은 자동화로 진행됩니다**\n"
            "**╰ 충전 중 문제 발생 시 문의해주세요**\n\n"
            "**[BloxFlip 이용약관](https://discord.com/channels/1449027775888494652/1449189661359608071)   [BloxFlip 문의하기](https://discord.com/channels/1449027775888494652/1449190798028443841)**"
        ), 
        color=0xffffff
    )

    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)

    await interaction.channel.send(embed=embed, view=EscrowView())

@bot.tree.command(name="인증패널", description="로블록스 인증하기 패널")
@app_commands.checks.has_permissions(administrator=True)
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("**DONE**", ephemeral=True)

    embed = discord.Embed(
        title="BloxFlip - 인증하기", 
        description=(
            "**╰ 인증 후 게임 이용이 가능합니다**\n"
            "**╰ 인증 중 문제 발생 시 문의해주세요**\n\n"
            "**[BloxFlip 이용약관](https://discord.com/channels/1449027775888494652/1449189661359608071)   [BloxFlip 문의하기](https://discord.com/channels/1449027775888494652/1449190798028443841)**"
        ), 
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)

    await interaction.channel.send(embed=embed, view=VerifyStartView())

@bot.tree.command(name="인증유저", description="인증된 유저 목록을 확인")
@app_commands.checks.has_permissions(administrator=True)
async def verify_info(interaction: discord.Interaction):
    db_data = load_db()
    view = VerifyInfoView(db_data)
    await interaction.response.send_message(embed=view.make_embed(), view=view, ephemeral=True)

@bot.tree.command(name="티켓패널", description="문의티켓 생성 패널 ")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="BloxFlip - 문의티켓",
        description=(
            "**╰ 티켓 생성 후 관리자 멘션해주세요**\n"
            "**╰ 문의 끝나면 txt파일로 기록이 저장됩니다**\n\n"
            "**[BloxFlip 이용약관](https://discord.com/channels/1449027775888494652/1449189661359608071)**"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)
    
    await interaction.response.send_message("**DONE**", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketLaunchView())

@bot.tree.command(name="봇상태", description="봇 실시간 상태 패널")
@app_commands.checks.has_permissions(administrator=True)
async def bot_state_cmd(interaction: discord.Interaction):
    global status_msg
    
    await interaction.response.defer(ephemeral=False) 
    
    embed = await create_bot_state_embed()
    status_msg = await interaction.followup.send(embed=embed)
    
    if not bot_status_loop.is_running():
        bot_status_loop.start()

@bot.tree.command(name="환전패널", description="환전하기 패널")
@app_commands.checks.has_permissions(administrator=True)
async def recharge_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="BloxFlip - 환전하기",
        description=(
            "**╰ 환전 중 문제 발생 시 문의해주세요**\n"
            "**╰ 환전한 기록들은 DB에 저장됩니다**\n\n"
            "**[BloxFlip 이용약관](https://discord.com/channels/1449027775888494652/1449189661359608071)   [BloxFlip 문의하기](https://discord.com/channels/1449027775888494652/1449190798028443841)**"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    embed.set_image(url=img_url)

    await interaction.response.send_message("**DONE**", ephemeral=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="베팅하기", description="코인플립 패널")
@app_commands.checks.has_permissions(administrator=True)
async def betting_command(interaction: discord.Interaction):
    start_embed = discord.Embed(
        title="BloxFlip - 베팅하기",
        description=(
            "**╰ 베팅 중 문제 발생 시 문의 부탁해주세요**\n"
            "**╰ 베팅한 기록들은 DB에 저장됩니다**\n\n"
            "**[BloxFlip 이용약관](https://discord.com/channels/1449027775888494652/1449189661359608071)   [BloxFlip 문의하기](https://discord.com/channels/1449027775888494652/1449190798028443841)**"
        ),
        color=0xffffff
    )
    img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
    start_embed.set_image(url=img_url)

    class StartView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="아이템 베팅하기", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="pig", id=1455997087228629043))
        async def start(self, interaction_start: discord.Interaction, button: discord.ui.Button):
            choice_view = CoinChoiceView()
            choice_embed = discord.Embed(title="BloxFlip - 베팅선택", description="**╰ 앞면 혹은 뒷면을 골라주세요\n╰ 확률은 50%입니다**", color=0xffffff)
            img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
            choice_embed.set_image(url=img_url)
            await interaction_start.response.send_message(embed=choice_embed, view=choice_view, ephemeral=True)

    await interaction.response.send_message("**DONE**", ephemeral=True)
    await interaction.channel.send(embed=start_embed, view=StartView())

@app.post("/trade/event")
async def handle_trade(request: Request):
    data = await request.json()
    action = data.get("action") 
    r_id = data.get("roblox_id")
    r_name = data.get("roblox_name")
    items = data.get("items")

    user_info = get_user_data(r_id)
    if user_info:
        d_id = user_info['discord_id']
        log_transaction(action, d_id, r_name, items)
        
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(CHANGE_WEBHOOK_URL, session=session)
            embed = discord.Embed(title=f"{action.upper()} 감지", color=0xffffff)
            embed.add_field(name="유저", value=f"```<@{d_id}>```", inline=True)
            embed.add_field(name="아이템", value=f"```\n{items}\n```")
            await webhook.send(embed=embed)
            
    return {"status": "ok"}

@bot.event
async def on_ready():
    print(f"DONE {bot.user}")

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    start_time = time.time()
    threading.Thread(target=run_api, daemon=True).start()
    bot.run('')
