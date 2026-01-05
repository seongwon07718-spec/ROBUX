from PIL import Image, ImageDraw
import math
import os

def create_final_large_flip(h_path, t_path, bg_path):
    if not all(os.path.exists(p) for p in [h_path, t_path, bg_path]):
        print("❌ 파일명을 확인하세요 (H.png, T.png, BloxF_background.png)")
        return

    def get_circular_crop(path):
        """코인을 원형으로 정밀하게 오려내어 배경 제거 오류 방지"""
        img = Image.open(path).convert("RGBA")
        width, height = img.size
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, width, height), fill=255)
        output = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output

    print("✂️ 코인 원형 정밀 커팅 중...")
    h_img = get_circular_crop(h_path)
    t_img = get_circular_crop(t_path)
    
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg_img.size

    # 1. 크기 확대: 노란색 구역을 꽉 채우도록 배경 높이의 45%로 키움
    coin_size = int(bg_h * 0.45) 
    h_img = h_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    t_img = t_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    
    total_frames = 120

    def generate(final_side, filename):
        frames = []
        print(f"🎬 {filename} 생성 중 (크기 확대 버전)...")
        
        for i in range(total_frames):
            t = i / total_frames
            progress = 1 - (1 - t)**3
            
            total_angle = 7200 if final_side == "H" else 7380
            angle = progress * total_angle
            
            rad = math.radians(angle)
            height_scale = abs(math.cos(rad))
            current_face = t_img if 90 < (angle % 360) < 270 else h_img
            
            # 수직 회전 리사이즈
            new_h = max(int(coin_size * height_scale), 1)
            resized_coin = current_face.resize((coin_size, new_h), Image.Resampling.LANCZOS)
            
            # 2. 위치 정밀 조정: 노란색 구역 중심 (Y축 약 60% 지점)
            frame = bg_img.copy()
            coin_x = (bg_w - coin_size) // 2
            # 커진 크기에 맞춰 Y 좌표를 살짝 위로 보정하여 노란색 구역에 안착
            coin_y = int(bg_h * 0.60) + (coin_size - new_h) // 2
            
            frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
            frames.append(frame)

        # 감속 타이밍 및 멈춤 화면
        durations = [10 + int(250 * ((i/total_frames)**3)) for i in range(total_frames)]
        durations.append(2500)

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, optimize=True)
        print(f"✅ {filename} 제작 완료!")

    generate("H", "large_yellow_H.gif")
    generate("T", "large_yellow_T.gif")

if __name__ == "__main__":
    create_final_large_flip("H.png", "T.png", "BloxF_background.png")
