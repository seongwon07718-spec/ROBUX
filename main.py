import discord
import json
import uuid
import aiohttp
import random
import math
import os
from PIL import Image, ImageDraw
from discord.ext import commands
from database import save_bet_info

# --- 로블록스 데이터 및 GIF 생성 함수 ---
def get_roblox_id(discord_id):
    try:
        with open('verified_users.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(discord_id)) # JSON 내의 디스코드 ID로 로블록스 ID 조회
    except: return None

async def get_roblox_thumb(roblox_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_id}&size=150x150&format=Png&isCircular=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data['data'][0]['imageUrl'] if data['data'] else None
    return "https://tr.rbxcdn.com/38c6dec17b8764831362e59a68688439/420/420/Image/Png"

def create_final_bet_gif(side, bg_path, h_path, t_path):
    def get_clean_side(img_path, size):
        img = Image.open(img_path).convert("RGBA")
        img = img.resize((size * 4, size * 4), Image.Resampling.LANCZOS)
        mask = Image.new('L', (size * 4, size * 4), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size * 4, size * 4), fill=255)
        clean = Image.new('RGBA', (size * 4, size * 4), (0, 0, 0, 0))
        clean.paste(img, (0, 0), mask=mask)
        return clean.resize((size, size), Image.Resampling.LANCZOS)

    bg = Image.open(bg_path).convert("RGBA")
    coin_size = int(bg.height * 0.45)
    h_img, t_img = get_clean_side(h_path, coin_size), get_clean_side(t_path, coin_size)
    frames = []
    total_frames = 120
    target_y = (bg.height // 2) + 50 # 중앙 하단 배치
    start_y = -300

    for i in range(total_frames):
        t = i / (total_frames - 1)
        progress = 1 - pow(1 - t, 4) # 수직 낙하 이징
        current_y = start_y + (target_y - start_y) * progress
        total_rot = 5400 if side == "H" else 5580
        angle = progress * total_rot
        scale = abs(math.cos(math.radians(angle)))
        current_coin = t_img if 90 < (angle % 360) < 270 else h_img
        new_h = max(int(coin_size * scale), 1)
        res_coin = current_coin.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        frame = bg.copy()
        frame.paste(res_coin, ((bg.width-coin_size)//2, int(current_y-(new_h//2))), res_coin)
        frames.append(frame)

    for _ in range(50): frames.append(frames[-1])
    frames[0].save(f"final_fix_{side}.gif", save_all=True, append_images=frames[1:], duration=25, loop=0, optimize=True, disposal=2)

# --- 디스코드 뷰 클래스 ---
class ResultShowView(discord.ui.View):
    def __init__(self, bet_id, c_data, p_data, result):
        super().__init__(timeout=None)
        self.bet_id, self.c, self.p, self.result = bet_id, c_data, p_data, result

    @discord.ui.button(label="VIEW", style=discord.ButtonStyle.success)
    async def view_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.c['id'], self.p['id']]:
            return await interaction.response.send_message("참여자 전용입니다.", ephemeral=True)
        
        filename = f"final_fix_{self.result}.gif"
        # GIF가 없다면 생성 (최초 1회)
        if not os.path.exists(filename):
            create_final_bet_gif(self.result, "BloxF_background.png", "H.png", "T.png")
            
        file = discord.File(filename, filename=filename)
        embed = discord.Embed(title="Bloxy Bet - Result", color=0xffffff)
        embed.add_field(name=f"👤 {self.c['name']}", value=f"Side: {self.c['side']}", inline=True)
        embed.add_field(name="VS", value="🔥", inline=True)
        embed.add_field(name=f"👤 {self.p['name']}", value=f"Side: {self.p['side']}", inline=True)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_author(name=f"Creator: {self.c['name']}", icon_url=self.c['thumb'])
        embed.set_thumbnail(url=self.p['thumb'])
        embed.set_footer(text=f"Bet ID: {self.bet_id}")
        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

class BettingProcessView(discord.ui.View):
    def __init__(self, creator, side, res):
        super().__init__(timeout=None)
        self.creator, self.side, self.res = creator, side, res

    @discord.ui.button(label="JOIN", style=discord.ButtonStyle.primary)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.creator.id:
            return await interaction.response.send_message("본인 게임 참가 불가", ephemeral=True)
        
        bet_id = str(uuid.uuid4())[:18] # 고유 ID 생성
        c_rid, p_rid = get_roblox_id(self.creator.id), get_roblox_id(interaction.user.id)
        c_thumb, p_thumb = await get_roblox_thumb(c_rid), await get_roblox_thumb(p_rid)
        
        c_data = {'id': self.creator.id, 'name': self.creator.display_name, 'thumb': c_thumb, 'side': self.side}
        p_data = {'id': interaction.user.id, 'name': interaction.user.display_name, 'thumb': p_thumb, 'side': 'T' if self.side == 'H' else 'H'}
        
        save_bet_info(bet_id, self.creator.id, interaction.user.id, self.res) # DB 저장
        
        new_view = ResultShowView(bet_id, c_data, p_data, self.res)
        await interaction.message.edit(view=new_view)
        await interaction.response.send_message("참가 완료! VIEW 버튼을 눌러주세요.", ephemeral=True)
