from PIL import Image, ImageDraw
import math
import os

def create_final_upgraded_flip(h_path, t_path, bg_path):
    if not all(os.path.exists(p) for p in [h_path, t_path, bg_path]):
        print("❌ 파일명을 다시 확인해주세요 (H.png, T.png, BloxF_background.png)")
        return

    def get_perfect_clean(path):
        """외곽 배경을 더 강력하게 제거하는 로직"""
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # thresh를 80으로 높여 미세한 잔상까지 제거 (문자는 안쪽이라 안전)
        # 상하좌우 모든 끝단에서 배경 제거 시도
        for x in [0, w-1]:
            for y in range(0, h, 10): 
                ImageDraw.floodfill(img, xy=(x, y), value=(0, 0, 0, 0), thresh=80)
        for y in [0, h-1]:
            for x in range(0, w, 10):
                ImageDraw.floodfill(img, xy=(x, y), value=(0, 0, 0, 0), thresh=80)
        return img

    print("🧼 코인 배경 강력 제거 중...")
    h_img = get_perfect_clean(h_path)
    t_img = get_perfect_clean(t_path)
    
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg_img.size

    # 1. 크기 확대: 배경 높이의 70% 수준으로 크게 조절
    coin_size = int(bg_h * 0.7)
    h_img = h_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    t_img = t_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    
    total_frames = 120

    def generate(final_side, filename):
        frames = []
        print(f"🎬 {filename} 생성 시작 (위치 상향)...")
        
        for i in range(total_frames):
            t = i / total_frames
            progress = 1 - (1 - t)**3
            
            total_angle = 7200 if final_side == "H" else 7380
            angle = progress * total_angle
            
            rad = math.radians(angle)
            height_scale = abs(math.cos(rad))
            
            current_face = t_img if 90 < (angle % 360) < 270 else h_img
            
            # 회전 리사이즈
            new_h = max(int(coin_size * height_scale), 1)
            resized_coin = current_face.resize((coin_size, new_h), Image.Resampling.LANCZOS)
            
            # 2. 위치 수정: 배경 복사 후 코인을 중앙보다 위로 배치
            frame = bg_img.copy()
            coin_x = (bg_w - coin_size) // 2
            # 중앙(bg_h-new_h)//2 보다 위쪽인 상단 20% 지점 부근으로 설정
            coin_y = int(bg_h * 0.15) + (coin_size - new_h) // 2
            
            frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
            frames.append(frame)

        # 자연스러운 감속 듀레이션
        durations = [10 + int(250 * ((i/total_frames)**3)) for i in range(total_frames)]
        durations.append(2500) # 정지 화면 조금 더 길게

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, optimize=True)
        print(f"✅ {filename} 완료!")

    generate("H", "upgraded_H.gif")
    generate("T", "upgraded_T.gif")

if __name__ == "__main__":
    create_final_upgraded_flip("H.png", "T.png", "BloxF_background.png")
