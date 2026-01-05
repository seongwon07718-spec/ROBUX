from PIL import Image, ImageDraw
import math
import os

def create_final_bg_flip(h_path, t_path, bg_path):
    if not all(os.path.exists(p) for p in [h_path, t_path, bg_path]):
        print("❌ 파일(H, T, 배경) 중 없는 것이 있습니다. 파일명을 확인하세요.")
        return

    def get_outer_clean(path):
        """외곽 배경만 선택적으로 제거하여 중앙 문자를 보호"""
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # 모서리에서 시작해 연결된 배경만 투명화
        ImageDraw.floodfill(img, xy=(0, 0), value=(0, 0, 0, 0), thresh=50)
        ImageDraw.floodfill(img, xy=(w-1, 0), value=(0, 0, 0, 0), thresh=50)
        return img

    print("🧹 코인 배경 제거 중...")
    h_img = get_outer_clean(h_path)
    t_img = get_outer_clean(t_path)
    
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg_img.size

    # 코인 크기 최적화 (배경 높이의 약 50%)
    coin_size = int(bg_h * 0.5)
    h_img = h_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    t_img = t_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    
    total_frames = 120

    def generate(final_side, filename):
        frames = []
        print(f"🎬 {filename} 생성 시작...")
        
        for i in range(total_frames):
            t = i / total_frames
            progress = 1 - (1 - t)**3 # 감속 곡선
            
            # 결과값에 따른 최종 각도 (H: 20바퀴, T: 20.5바퀴)
            total_angle = 7200 if final_side == "H" else 7380
            angle = progress * total_angle
            
            rad = math.radians(angle)
            height_scale = abs(math.cos(rad))
            
            # 현재 면 선택
            current_face = t_img if 90 < (angle % 360) < 270 else h_img
            
            # 회전 리사이즈
            new_h = max(int(coin_size * height_scale), 1)
            resized_coin = current_face.resize((coin_size, new_h), Image.Resampling.LANCZOS)
            
            # 배경에 합성
            frame = bg_img.copy()
            coin_x = (bg_w - coin_size) // 2
            coin_y = (bg_h - new_h) // 2
            frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
            frames.append(frame)

        # 듀레이션 및 정지 화면
        durations = [10 + int(250 * ((i/total_frames)**3)) for i in range(total_frames)]
        durations.append(2000)
        frames.append(frames[-1])

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, optimize=True)
        print(f"✅ {filename} 완료!")

    generate("H", "final_H_bg.gif")
    generate("T", "final_T_bg.gif")

if __name__ == "__main__":
    # 배경 파일명을 'BloxF_background.png'로 맞춰주세요.
    create_final_bg_flip("H.png", "T.png", "BloxF_background.png")
