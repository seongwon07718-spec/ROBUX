import discord
import json
import uuid
import aiohttp
import io
import os
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from database import save_bet_info

# --- 로블록스 데이터 연동 ---
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

# --- GIF 실시간 합성 함수 (Bloxybet 스타일) ---
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

# --- 결과 전송 뷰 ---
class ResultShowView(discord.ui.View):
    def __init__(self, bet_id, c_data, p_data, result):
        super().__init__(timeout=None)
        self.bet_id, self.c, self.p, self.result = bet_id, c_data, p_data, result

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
