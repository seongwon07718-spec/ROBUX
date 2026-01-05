from PIL import Image
import math
import os

def create_vertical_flip_gif(h_path, t_path, output_name="coinflip_vertical.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    total_frames = 45 # 더 부드러운 연출을 위해 프레임 증가
    
    print("🎬 위아래 입체 회전 렌더링 중...")

    for i in range(total_frames):
        # 1. 진행도(t)에 따른 비선형 회전 각도 (감속 적용)
        t = i / total_frames
        # 약 4바퀴 회전하며 멈춤
        angle = (t * (2 - t)) * 1440 
        
        rad = math.radians(angle)
        sin_val = math.sin(rad)
        cos_val = math.cos(rad)
        
        # 2. 위아래 회전 핵심: 세로 높이($h$)를 조절
        # 높이가 0에 가까워질 때 면이 바뀜
        height_scale = abs(cos_val)
        
        # 3. 원근감 및 바운스 (위로 던져지는 느낌)
        # 코인이 정면을 볼 때 살짝 더 크게(1.1배), 측면일 때 작게
        perspective_scale = 1.0 + (0.1 * abs(sin_val))
        jump_height = 50 * math.sin(math.pi * t) # 포물선 점프
        
        # 앞/뒤 면 결정 (위아래 회전각 기준)
        if (angle % 360) > 90 and (angle % 360) < 270:
            current_base = t_img
        else:
            current_base = h_img
            
        # 크기 변형 적용
        new_w = int(w * perspective_scale)
        new_h = max(int(h * height_scale * perspective_scale), 1)
        resized = current_base.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 캔버스 생성 (점프 높이 고려)
        canvas_h = h + 100
        canvas_w = w + 40
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        
        # 중앙 배치 및 바운스 적용
        x_pos = (canvas_w - new_w) // 2
        y_pos = int((canvas_h - new_h) // 2 - jump_height)
        canvas.paste(resized, (x_pos, y_pos))
        frames.append(canvas)

    # 결과 정지 화면 (2초)
    # 마지막 프레임을 결과값에 맞춰 고정 (여기선 앞면 기준)
    for _ in range(20):
        frames.append(frames[-1])

    # 4. Bloxluck 특유의 드르륵 멈추는 속도감
    durations = []
    for i in range(total_frames):
        # 초반 20ms에서 후반 500ms까지 부드럽게 느려짐
        d = 15 + int(485 * (i / total_frames)**4) 
        durations.append(d)
    durations.extend([2000] * 20)

    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, disposal=2
    )
    print(f"✅ 위아래 회전 완성: {output_name}")

if __name__ == "__main__":
    create_vertical_flip_gif("H.png", "T.png")
