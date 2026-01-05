from PIL import Image, ImageTransform
import math
import os

def create_realistic_coin_gif(h_path, t_path, output_name="coinflip_pro.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 폴더에 없습니다.")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    total_frames = 40 # 프레임 수를 늘려 훨씬 부드럽게
    
    print("🚀 물리 엔진 적용 중... (입체 회전 및 감속 연출)")

    for i in range(total_frames):
        # 1. 물리적 회전 각도 계산 (갈수록 느려지는 감속 비율 적용)
        # 진행도(t)를 0에서 1로 설정하여 비선형적으로 회전
        t = i / total_frames
        angle = (t * (2 - t)) * 1440 # 4바퀴 회전하면서 마지막에 감속
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 입체감(원근) 구현: 가로 너비와 세로 높이를 동시에 조절
        # 코인이 옆면일 때 약간 작아지게 하여 원근감 부여
        width_scale = abs(cos_val)
        height_scale = 1.0 + (0.05 * abs(math.sin(rad))) # 회전 시 미세한 높이 변화
        
        # 3. 바운스 효과: 코인이 공중으로 떴다가 내려오는 느낌
        # 포물선 운동 추가 (y축 오프셋)
        jump_height = 40 * math.sin(math.pi * t) 
        
        # 앞/뒤 이미지 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 이미지 변형
        new_w = max(int(w * width_scale), 1)
        new_h = int(h * height_scale)
        resized = current_base.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 캔버스 생성 (바운스 높이 고려하여 높이를 약간 크게 잡음)
        canvas_h = h + 60
        canvas = Image.new("RGBA", (w, canvas_h), (0, 0, 0, 0))
        
        # 중앙 배치 및 점프 적용
        y_pos = int((canvas_h - new_h) // 2 - jump_height)
        canvas.paste(resized, ((w - new_w) // 2, y_pos))
        frames.append(canvas)

    # 최종 결과 멈춤 (2초)
    for _ in range(20):
        frames.append(frames[-1])

    # 4. 프레임당 속도 조절 (ms)
    # 처음엔 초당 50프레임 속도(20ms), 마지막엔 천천히 멈춤
    durations = []
    for i in range(total_frames):
        d = 20 + int(200 * (i / total_frames)**3) # 3제곱 비례로 급감속
        durations.append(d)
    durations.extend([2000] * 20)

    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, disposal=2
    )
    print(f"✅ 자연스러운 코인플립 완성: {output_name}")

if __name__ == "__main__":
    create_realistic_coin_gif("H.png", "T.png")
