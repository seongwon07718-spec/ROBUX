from PIL import Image
import math
import os

def create_fast_stop_flip(h_path, t_path, output_name="coin_fast.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 프레임을 150장으로 압축하여 속도감 상승
    total_frames = 150 
    
    print("🚀 짧고 강렬한 연출 생성 중...")

    for i in range(total_frames):
        # 속도 곡선: 0.7 지점까지 광속, 이후 급격히 감속하여 정지
        t = i / total_frames
        if t < 0.7:
            progress = t * 1.2 # 초반 가속
        else:
            # 마지막 30% 구간에서 짧고 굵게 감속
            sub_t = (t - 0.7) / 0.3
            progress = 0.84 + (0.16 * (1 - (1 - sub_t)**2))
            
        angle = progress * 5400 # 총 15바퀴 회전
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 수직 회전 (높이만 조절)
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.NEAREST) # 속도를 위해 NEAREST 사용
        
        canvas = Image.new("RGBA", (w, h), (255, 255, 255, 255)) # 흰 배경 유지
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 듀레이션 설정 (전체 약 3~4초 내외)
    durations = []
    for i in range(total_frames):
        if i < 100:
            d = 10 # 초반 광속 (10ms)
        else:
            # 급격한 감속
            ease_t = (i - 100) / 50
            d = 10 + int(150 * (ease_t**2))
        durations.append(d)

    # 정지 화면 (1.5초만 짧게)
    durations.append(1500)
    frames.append(frames[-1])

    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        optimize=True
    )
    print(f"✅ 완성: {output_name}")

if __name__ == "__main__":
    create_fast_stop_flip("
