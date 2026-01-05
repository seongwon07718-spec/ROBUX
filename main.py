import discord
from discord.ext import commands
from discord.ui import Button, View
from PIL import Image, ImageDraw
import math
import random
import io

# --- 1. 매끄러운 마감의 GIF 생성 함수 ---
def create_smooth_gif(side, bg_path, h_path, t_path):
    # 슈퍼샘플링 (4배 크게 작업 후 축소하여 테두리를 부드럽게 만듦)
    def get_smooth_mask(img_path, size):
        img = Image.open(img_path).convert("RGBA")
        upscale_size = size * 4
        mask = Image.new('L', (upscale_size, upscale_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, upscale_size, upscale_size), fill=255)
        
        img = img.resize((upscale_size, upscale_size), Image.Resampling.LANCZOS)
        output = Image.new('RGBA', (upscale_size, upscale_size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output.resize((size, size), Image.Resampling.LANCZOS)

    bg = Image.open(bg_path).convert("RGBA")
    coin_size = int(bg.height * 0.5) # 크기 키움
    h_img = get_smooth_mask(h_path, coin_size)
    t_img = get_smooth_mask(t_path, coin_size)
    
    frames = []
    total_frames = 80 # 부드러운 회전을 위해 프레임 수 조절
    
    for i in range(total_frames):
        t = i / total_frames
        progress = 1 - (1 - t)**3
        angle = progress * (7200 if side == "H" else 7380)
        
        rad = math.radians(angle)
        scale = abs(math.cos(rad))
        current = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(coin_size * scale), 1)
        resized = current.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        
        frame = bg.copy()
        coin_x = (bg.width - coin_size) // 2
        coin_y = int(bg.height * 0.42) - (new_h // 2) # 노란 박스 위치
        frame.paste(resized, (coin_x, coin_y), resized)
        frames.append(frame)

    # 메모리에 GIF 저장 (속도 향상)
    out = io.BytesIO()
    frames[0].save(out, format='GIF', save_all=True, append_images=frames[1:], duration=30, loop=0)
    out.seek(0)
    return out

# --- 2. 디스코드 봇 베팅 시스템 ---
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

@bot.command(name="베팅하기")
async def start_bet(ctx):
    # [1단계] 시작 임베드
    embed = discord.Embed(
        title="🎲 BloxFlip 코인플립", 
        description="코인플립 베팅을 시작하시겠습니까?", 
        color=0x5865F2
    )
    view = View()
    btn_start = Button(label="베팅 시작하기", style=discord.ButtonStyle.primary)

    async def start_callback(interaction):
        # [2단계] H / T 선택 (아이템 선택 건너뜀)
        embed_choice = discord.Embed(
            title="🪙 앞면(H)인가 뒷면(T)인가?", 
            description="원하는 면을 선택해주세요!", 
            color=0xFFCC00
        )
        view_choice = View()
        btn_h = Button(label="앞면 (H)", style=discord.ButtonStyle.danger)
        btn_t = Button(label="뒷면 (T)", style=discord.ButtonStyle.primary)

        async def flip_callback(interaction_choice, user_side):
            # 베팅 결과 계산
            result_side = random.choice(["H", "T"])
            is_win = (user_side == result_side)
            
            # [3단계] 결과 대기 임베드
            embed_wait = discord.Embed(
                title="📣 베팅 완료!", 
                description=f"{interaction_choice.user.mention}님이 **{user_side}**에 베팅했습니다!", 
                color=0x2ecc71
            )
            view_wait = View()
            btn_result = Button(label="결과보기", style=discord.ButtonStyle.success)

            async def result_callback(interaction_res):
                # GIF 생성 및 전송
                await interaction_res.response.defer() # 생성 시간 고려해 응답 지연 처리
                gif_data = create_smooth_gif(result_side, "BloxF_background.png", "H.png", "T.png")
                gif_file = discord.File(gif_data, filename="result.gif")
                
                final_embed = discord.Embed(
                    title="🎊 결과 발표!", 
                    description=f"결과는 **{result_side}**입니다!\n" + ("✅ **승리하셨습니다!**" if is_win else "❌ **아쉽게 패배하셨습니다.**"),
                    color=0x2ecc71 if is_win else 0xe74c3c
                )
                final_embed.set_image(url="attachment://result.gif")
                await interaction_res.followup.send(embed=final_embed, file=gif_file)

            btn_result.callback = result_callback
            view_wait.add_item(btn_result)
            await interaction_choice.response.edit_message(embed=embed_wait, view=view_wait)

        btn_h.callback = lambda i: flip_callback(i, "H")
        btn_t.callback = lambda i: flip_callback(i, "T")
        view_choice.add_item(btn_h)
        view_choice.add_item(btn_t)
        await interaction.response.edit_message(embed=embed_choice, view=view_choice)

    btn_start.callback = start_callback
    view.add_item(btn_start)
    await ctx.send(embed=embed, view=view)

bot.run("YOUR_TOKEN")
