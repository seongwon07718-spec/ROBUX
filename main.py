from PIL import Image, ImageDraw
import math

def create_bloxy_clean_drop(side, bg_path, h_path, t_path):
    # 1. 안티앨리어싱 적용 (테두리 부드럽게)
    def get_smooth_img(img_path, size):
        img = Image.open(img_path).convert("RGBA")
        img = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
        return img.resize((size, size), Image.Resampling.LANCZOS)

    bg = Image.open(bg_path).convert("RGBA")
    coin_size = int(bg.height * 0.45)
    h_img = get_smooth_img(h_path, coin_size)
    t_img = get_smooth_img(t_path, coin_size)

    frames = []
    total_frames = 75  # 디스코드 최적화 프레임 (렉 방지)
    
    target_y = bg.height // 2 # 최종 멈출 중앙 지점
    start_y = -200            # 위쪽 화면 밖에서 시작

    for i in range(total_frames):
        t = i / (total_frames - 1)
        
        # 2. Quintic Out: 위에서 아래로 빠르게 떨어지다가 중앙에서 '탁' 멈춤 (아래로 안 내려감)
        progress = 1 - pow(1 - t, 5) 
        
        # 현재 위치 (Y축) - 오직 위에서 아래로만 이동
        current_y = start_y + (target_y - start_y) * progress
        
        # 회전수 설정 (멈출 때 앞/뒷면 결정)
        total_rotation = 3600 if side == "H" else 3780
        angle = progress * total_rotation
        
        rad = math.radians(angle)
        scale = abs(math.cos(rad))
        current_coin = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 코인 렌더링
        new_h = max(int(coin_size * scale), 1)
        resized_coin = current_coin.resize((coin_size, new_h), Image.Resampling.LANCZOS)
        
        # 배경에 합성 (잔상 제거를 위해 매번 새 복사본 사용)
        frame = bg.copy()
        coin_x = (bg.width - coin_size) // 2
        coin_y = int(current_y - (new_h // 2))
        
        frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
        frames.append(frame)

    # 마지막 프레임(멈춘 상태) 1.5초 유지 (결과 확인 시간)
    for _ in range(30):
        frames.append(frames[-1])

    # 3. 최적화 저장 (렉 최소화 설정)
    frames[0].save(
        f"final_fix_{side}.gif",
        save_all=True,
        append_images=frames[1:],
        duration=20,     # 50 FPS (디스코드에서 가장 부드러운 속도)
        loop=0,
        optimize=True,   # 용량 최적화로 렉 방지
        disposal=2       # 프레임 전환 시 잔상 삭제
    )

# 실행 (H, T 생성)
# create_bloxy_clean_drop("H", "BloxF_background.png", "H.png", "T.png")
# create_bloxy_clean_drop("T", "BloxF_background.png", "H.png", "T.png")
