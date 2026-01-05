from PIL import Image, ImageDraw
import math
import io

def create_super_smooth_gif(side, bg_path, h_path, t_path):
    # 고화질 안티앨리어싱 마스크 처리
    def get_smooth_img(img_path, size):
        img = Image.open(img_path).convert("RGBA")
        upscale = size * 4
        img = img.resize((upscale, upscale), Image.Resampling.LANCZOS)
        mask = Image.new('L', (upscale, upscale), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, upscale, upscale), fill=255)
        output = Image.new('RGBA', (upscale, upscale), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output.resize((size, size), Image.Resampling.LANCZOS)

    bg = Image.open(bg_path).convert("RGBA")
    coin_size = int(bg.height * 0.45)
    h_img = get_smooth_img(h_path, coin_size)
    t_img = get_smooth_img(t_path, coin_size)

    frames = []
    # 1. 프레임 수를 120개로 늘려 60FPS에 가깝게 구현 (끊김 방지)
    total_frames = 120 
    
    target_y = bg.height // 2
    start_y = bg.height + 150 # 화면 밖 아래에서 시작

    for i in range(total_frames):
        t = i / (total_frames - 1)
        
        # 2. Quintic Out 이징: Cubic보다 더 급격하게 올라와서 아주 부드럽게 감속
        progress = 1 - pow(1 - t, 5) 
        
        # 위치 및 회전 계산
        current_y = start_y + (target_y - start_y) * progress
        total_rotation = 7200 if side == "H" else 7380
        angle = progress * total_rotation
        
        rad = math.radians(angle)
        scale = abs(math.cos(rad))
        current_coin = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 부드러운 리사이징
        new_h = max(int(coin_size * scale), 1)
        resized_coin = current_coin.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        
        frame = bg.copy()
        coin_x = (bg.width - coin_size) // 2
        coin_y = int(current_y - (new_h // 2))
        
        frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
        frames.append(frame)

    # 마지막 정지 화면 유지
    for _ in range(15):
        frames.append(frames[-1])

    # 3. duration을 15ms~20ms로 설정하여 매우 빠르게 재생 (부드러움의 핵심)
    frames[0].save(
        f"final_fix_{side}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=18, 
        loop=0,
        disposal=2 # 잔상 방지 설정
    )

# 실행 (H, T 각각 생성)
create_super_smooth_gif("H", "BloxF_background.png", "H.png", "T.png")
create_super_smooth_gif("T", "BloxF_background.png", "H.png", "T.png")
