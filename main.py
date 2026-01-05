from PIL import Image, ImageDraw, ImageOps
import math

def create_final_bet_gif(side, bg_path, h_path, t_path):
    # 1. 배경 제거 및 안티앨리어싱 처리 함수 (복구)
    def get_clean_side(img_path, size):
        img = Image.open(img_path).convert("RGBA")
        # 화질 저하 방지를 위해 크게 작업 후 축소
        img = img.resize((size * 4, size * 4), Image.Resampling.LANCZOS)
        
        # 원형 마스크 생성 (배경 제거 효과)
        mask = Image.new('L', (size * 4, size * 4), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size * 4, size * 4), fill=255)
        
        clean_img = Image.new('RGBA', (size * 4, size * 4), (0, 0, 0, 0))
        clean_img.paste(img, (0, 0), mask=mask)
        return clean_img.resize((size, size), Image.Resampling.LANCZOS)

    bg = Image.open(bg_path).convert("RGBA")
    coin_size = int(bg.height * 0.45)
    h_img = get_clean_side(h_path, coin_size)
    t_img = get_clean_side(t_path, coin_size)

    frames = []
    # 재생 시간을 늘리기 위해 프레임 수 증가 (약 4~5초 분량)
    total_frames = 120 
    
    # 2. 배치 수정: 중앙(bg.height // 2)에서 50픽셀 정도 더 아래로 설정
    target_y = (bg.height // 2) + 50 
    start_y = -300 # 화면 위쪽 더 높은 곳에서 시작

    for i in range(total_frames):
        t = i / (total_frames - 1)
        
        # 가감속 (Quintic Out): 더 천천히 떨어지며 무게감 있게 안착
        progress = 1 - pow(1 - t, 4) 
        
        current_y = start_y + (target_y - start_y) * progress
        
        # 회전수 증가 (더 오래 돌아가게 함)
        total_rotation = 5400 if side == "H" else 5580
        angle = progress * total_rotation
        
        rad = math.radians(angle)
        scale = abs(math.cos(rad))
        current_coin = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 코인 크기 변형
        new_h = max(int(coin_size * scale), 1)
        resized_coin = current_coin.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        
        frame = bg.copy()
        coin_x = (bg.width - coin_size) // 2
        coin_y = int(current_y - (new_h // 2))
        
        frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
        frames.append(frame)

    # 3. 마지막 멈춘 화면 유지 시간 대폭 증가 (약 2초 유지)
    for _ in range(50):
        frames.append(frames[-1])

    # 최종 저장 (부드러운 속도 유지)
    frames[0].save(
        f"final_fix_{side}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=25,     # 너무 빠르지도 느리지도 않은 속도
        loop=0,
        optimize=True,
        disposal=2
    )

# 실행
# create_final_bet_gif("H", "BloxF_background.png", "H.png", "T.png")
# create_final_bet_gif("T", "BloxF_background.png", "H.png", "T.png")
