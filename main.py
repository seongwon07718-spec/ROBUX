from PIL import Image, ImageDraw
import math

def create_bloxy_style_drop_gif(side, bg_path, h_path, t_path):
    # 고화질 샘플링 함수
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
    # 프레임 수를 대폭 늘려 끊김 현상 제거 (디바이스 한계치인 100~120 프레임)
    total_frames = 150 
    
    target_y = bg.height // 2  # 중앙 멈춤 지점
    start_y = -200             # 화면 위쪽 밖에서 시작

    for i in range(total_frames):
        t = i / (total_frames - 1)
        
        # --- 핵심: 위에서 떨어지는 Bounce 효과 (Elastic Out 이징) ---
        if t == 0: progress = 0
        elif t == 1: progress = 1
        else:
            p = 0.3
            progress = pow(2, -10 * t) * math.sin((t - p / 4) * (2 * math.pi) / p) + 1
        
        # 현재 Y 위치 (위에서 중앙으로)
        current_y = start_y + (target_y - start_y) * progress
        
        # 회전 속도 조절 (초반에 빠르게 돌다가 멈춤)
        total_rotation = 10800 if side == "H" else 10980
        angle = (1 - pow(1 - t, 3)) * total_rotation
        
        rad = math.radians(angle)
        scale = abs(math.cos(rad))
        current_coin = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 코인 크기 변형 (회전 효과)
        new_h = max(int(coin_size * scale), 1)
        resized_coin = current_coin.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        
        frame = bg.copy()
        coin_x = (bg.width - coin_size) // 2
        coin_y = int(current_y - (new_h // 2))
        
        frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
        frames.append(frame)

    # 멈춤 상태 유지
    for _ in range(20):
        frames.append(frames[-1])

    # 10ms (0.01초) 간격으로 저장 (디스코드 GIF가 지원하는 가장 빠른 속도)
    frames[0].save(
        f"final_fix_{side}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=10, 
        loop=0,
        disposal=2
    )

# 실행
# create_bloxy_style_drop_gif("H", "BloxF_background.png", "H.png", "T.png")
