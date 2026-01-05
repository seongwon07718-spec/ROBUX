from PIL import Image
import math
import os

def create_7s_extreme_flip(h_path, t_path, output_name="coin_7s.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    # 1. 이미지 로드 및 배경 투명화 유지
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    total_frames = 500 # 7초를 채울 촘촘한 프레임
    
    print("🔥 7초 광속 회전 연출 시작...")

    for i in range(total_frames):
        # 2. 속도 곡선: 초반엔 미친듯이 빠르고, 뒤로 갈수록 급격히 느려짐
        t = i / total_frames
        # 지수 감속 (t=0일 때 속도 최대, t=1일 때 정지)
        progress = 1 - (1 - t)**4 
        angle = progress * 10800 # 7초 동안 총 30바퀴 회전
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 3. 수직 회전 및 배경 제거 상태 유지
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 흰색 배경 없이 투명한 캔버스 생성
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos), resized) # 마스크 적용으로 투명도 유지
        frames.append(canvas)

    # 4. 7초 타이밍 맞춤 (총 7000ms)
    durations = []
    for i in range(total_frames):
        if i < 350:
            d = 5 # 초반 350프레임은 눈에 안 보일 정도로 광속 (5ms)
        else:
            # 나머지 150프레임 동안 남은 시간을 지수적으로 늘려 감속
            ease_t = (i - 350) / 150
            d = 5 + int(300 * (ease_t**3))
        durations.append(d)

    # 마지막 정지 화면 3초 추가
    durations.extend([3000])
    frames.append(frames[-1])

    # 5. 저장 (disposal=2로 잔상 및 흰 배경 완벽 제거)
    print("💾 저장 중... 용량이 크니 잠시만 기다려주세요.")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, transparency=0, optimize=True
    )
    print(f"✅ 7초 연출 완료: {output_name}")

if __name__ == "__main__":
    create_7s_extreme_flip("H.png", "T.png")
