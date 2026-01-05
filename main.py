from PIL import Image
import math
import os

def create_final_stationary_flip(h_path, t_path, output_name="coin_final_stationary.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    # 배경 없이 깔끔하게 투명도 유지 (RGBA)
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 부드러움과 성능의 최적점 (120프레임)
    total_frames = 120 
    
    print("🎬 제자리 광속 회전 렌더링 중...")

    for i in range(total_frames):
        t = i / total_frames
        
        # 1. 속도 곡선: 초반엔 직선적으로 빠르고, 후반에 큐빅 감속 적용
        # progress가 1에 가까워질수록 회전 속도가 0에 수렴
        progress = 1 - (1 - t)**3
        angle = progress * 7200 # 총 20바퀴 광속 회전
        
        rad = math.radians(angle)
        height_scale = abs(math.cos(rad))
        
        # 앞/뒤 면 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 2. 수직 회전 리사이즈 (LANCZOS 필터로 선명도 유지)
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 투명 배경 캔버스 (옆으로 안 움직이고 제자리 고정)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos), resized)
        frames.append(canvas)

    # 4. 프레임 타이밍 설정 (총 약 4~5초 연출)
    durations = []
    for i in range(total_frames):
        if i < 80:
            d = 10 # 초반 80프레임은 광속 (0.01초)
        else:
            # 마지막 40프레임 동안 서서히 감속
            ease_t = (i - 80) / 40
            d = 10 + int(250 * (ease_t**3))
        durations.append(d)

    # 마지막 정지 화면 2초 (결과 확인용)
    durations.append(2000)
    frames.append(frames[-1])

    # 5. 저장 (disposal=2로 잔상 제거 필수)
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 제자리 회전 완성: {output_name}")

if __name__ == "__main__":
    create_final_stationary_flip("H.png", "T.png")
