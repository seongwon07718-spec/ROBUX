from PIL import Image, ImageFilter
import math
import os

def create_extreme_smooth_gif(h_path, t_path, output_name="coinflip_extreme.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ 파일이 없습니다.")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    total_frames = 300 # 극한의 300프레임
    
    print("💎 초고품질 모션 블러 렌더링 중... (300 Frames)")

    for i in range(total_frames):
        # 1. 5차 함수(Quintic) 기반의 극단적 감속 곡선
        t = i / total_frames
        progress = 1 - (1 - t)**5
        angle = progress * 3600 # 총 10바퀴 회전
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 수직 회전 및 높이 조절
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 🔥 모션 블러(Motion Blur) 엔진
        # 초반 150프레임까지는 속도에 비례하여 블러 처리
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        
        if i < 120: # 초고속 구간
            blur_strength = (1 - (i / 120)) * 2 # 갈수록 흐림 효과 감소
            canvas = canvas.filter(ImageFilter.GaussianBlur(radius=blur_strength))
            
        frames.append(canvas)

    # 결과 고정 (4초)
    for _ in range(60):
        frames.append(frames[-1])

    # 4. 프레임 타이밍 정밀 튜닝
    durations = []
    for i in range(total_frames):
        # 10ms 고정으로 가다가 마지막에 아주 미세하게 0.001초 단위로 감속
        if i < 200:
            d = 10 # 100FPS급 속도
        else:
            ease_t = (i - 200) / 100
            d = 10 + int(800 * (ease_t**6)) # 6제곱 곡선으로 쫀득하게 멈춤
        durations.append(d)
    durations.extend([4000] * 60)

    # 5. 최종 저장 (이미지 최적화 포함)
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 극한의 부드러움 완성: {output_name}")

if __name__ == "__main__":
    create_extreme_smooth_gif("H.png", "T.png")
