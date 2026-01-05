from PIL import Image
import math
import os

def create_perfect_transparent_flip(h_path, t_path, output_name="coin_final_120.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    def get_clean_mask(img, tolerance=30):
        # 1. 배경색 추출 (좌측 상단 첫 픽셀)
        img = img.convert("RGBA")
        datas = img.getdata()
        bg_color = datas[0]
        
        new_data = []
        for item in datas:
            # 2. 색상 거리 계산 (배경색과 현재 픽셀의 차이)
            dist = math.sqrt(sum([(a - b) ** 2 for a, b in zip(item[:3], bg_color[:3])]))
            
            # 오차 범위 내에 있으면 투명 처리, 아니면 유지
            if dist < tolerance:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        return img

    print("🧼 배경 정밀 제거 중 (H, T 동일 적용)...")
    h_img = get_clean_mask(Image.open(h_path))
    t_img = get_clean_mask(Image.open(t_path))
    w, h = h_img.size
    
    frames = []
    total_frames = 120 
    
    print(f"🎬 120프레임 렌더링 시작...")

    for i in range(total_frames):
        t = i / total_frames
        progress = 1 - (1 - t)**3
        angle = progress * 5400 # 자연스러운 회전을 위해 15바퀴
        
        rad = math.radians(angle)
        height_scale = abs(math.cos(rad))
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 투명 캔버스 생성
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos), resized)
        frames.append(canvas)

    # 듀레이션 설정 (자연스러운 감속)
    durations = []
    for i in range(total_frames):
        if i < 80:
            d = 15 # 초반 광속
        else:
            ease_t = (i - 80) / 40
            d = 15 + int(250 * (ease_t**3))
        durations.append(d)

    durations.append(2000)
    frames.append(frames[-1])

    print("💾 저장 중...")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 완성: {output_name}")

if __name__ == "__main__":
    create_perfect_transparent_flip("H.png", "T.png")
