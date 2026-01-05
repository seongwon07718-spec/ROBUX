from PIL import Image
import math
import os

def create_7s_ultra_smooth_gif(h_path, t_path, output_name="coinflip_7s.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다!")
        return

    # RGBA 모드로 불러와서 투명 배경 유지
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    total_frames = 2500 # 7초를 채우기 위한 압도적 프레임 수
    
    print("🚀 7초 고정 연출 생성 중... (배경 제거 및 초정밀 감속 적용)")

    for i in range(total_frames):
        # 1. 7초 연출을 위한 감속 곡선 (지수함수 적용)
        t = i / total_frames
        # 처음엔 미친듯이 돌다가 7초에 맞춰서 서서히 멈춤
        progress = 1 - (1 - t)**5
        angle = progress * 10800 # 총 30바퀴 회전 (속도감 극대화)
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 수직 회전 (높이만 조절)
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        # 선명한 화질을 위해 LANCZOS 필터 사용
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 투명 배경 캔버스 (흰색 배경 삭제)
        # (0, 0, 0, 0)은 완전 투명을 의미합니다.
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 4. 7초(7000ms) 타이밍 정밀 배분
    durations = []
    for i in range(total_frames):
        # 초반 1800프레임은 1~2ms로 초광속 재생
        if i < 1800:
            d = 2
        else:
            # 마지막 700프레임 동안 2ms에서 100ms까지 지수적으로 감속
            ease_t = (i - 1800) / 700
            d = 2 + int(98 * (ease_t**6))
        durations.append(d)

    # 결과 고정 (결과 확인용 3초 추가)
    durations.extend([3000] * 30)
    for _ in range(30):
        frames.append(frames[-1])

    # 5. 저장 (disposal=2 옵션으로 프레임 겹침 방지)
    print("💾 저장 중... 2500프레임이라 시간이 조금 걸립니다.")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 7초 극한의 부드러움 완성: {output_name}")

if __name__ == "__main__":
    create_7s_ultra_smooth_gif("H.png", "T.png")
