from PIL import Image, ImageDraw
import math
import os

def create_final_safe_flip(h_path, t_path, bg_path):
    if not all(os.path.exists(p) for p in [h_path, t_path, bg_path]):
        print("❌ 파일명을 확인하세요 (H.png, T.png, BloxF_background.png)")
        return

    def get_circular_crop(path):
        """색상 분석 없이 코인을 동그랗게 오려내는 마스크 로직"""
        img = Image.open(path).convert("RGBA")
        width, height = img.size
        
        # 1. 픽셀 단위의 정밀한 원형 마스크 생성
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        # 이미지의 가장자리에 딱 맞게 원을 그림
        draw.ellipse((0, 0, width, height), fill=255)
        
        # 2. 마스크 적용 (원 바깥쪽은 완벽하게 투명화)
        output = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        return output

    print("✂️ 코인을 원형으로 정밀하게 오려내는 중...")
    h_img = get_circular_crop(h_path)
    t_img = get_circular_crop(t_path)
    
    bg_img = Image.open(bg_path).convert("RGBA")
    bg_w, bg_h = bg_img.size

    # 1. 크기 조절: 텍스트와 겹치지 않게 배경 높이의 35%로 축소
    coin_size = int(bg_h * 0.35)
    h_img = h_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    t_img = t_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
    
    total_frames = 120

    def generate(final_side, filename):
        frames = []
        print(f"🎬 {filename} 생성 중 (상단 배치)...")
        
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
            
            # 2. 위치 수정: 텍스트 영역을 피해 배경의 상단 10% 지점으로 더 올림
            frame = bg_img.copy()
            coin_x = (bg_w - coin_size) // 2
            # 화면 맨 위에서 살짝 떨어진 위치
            coin_y = int(bg_h * 0.1) + (coin_size - new_h) // 2
            
            frame.paste(resized_coin, (coin_x, coin_y), resized_coin)
            frames.append(frame)

        # 감속 타이밍 및 멈춤 화면
        durations = [10 + int(250 * ((i/total_frames)**3)) for i in range(total_frames)]
        durations.append(2500)

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, optimize=True)
        print(f"✅ {filename} 제작 완료!")

    generate("H", "final_H_fixed.gif")
    generate("T", "final_T_fixed.gif")

if __name__ == "__main__":
    create_final_safe_flip("H.png", "T.png", "BloxF_background.png")
