from PIL import Image
import math
import os

def create_smooth_stop_flip(h_path, t_path, output_name="coin_smooth_final.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ 파일이 없습니다.")
        return

    # 배경 제거 없이 흰 배경으로 속도 우선 처리
    h_img = Image.open(h_path).convert("RGB")
    t_img = Image.open(t_path).convert("RGB")
    w, h = h_img.size
    
    frames = []
    # 렉과 부드러움의 최적 균형점
    total_frames = 120 
    
    print("✨ 자연스러운 감속 렌더링 중...")

    for i in range(total_frames):
        # 1. 자연스러운 감속 곡선 (Sin 곡선 활용)
        # i=0일 때 변화량이 가장 크고(빠름), i=total_frames일 때 0에 수렴(멈춤)
        t = i / total_frames
        # 회전 각도 계산: 마지막에 아주 부드럽게 멈추도록 설정
        angle = math.sin(t * (math.pi / 2)) * 3600 # 총 10바퀴
        
        rad = math.radians(angle)
        height_scale = abs(math.cos(rad))
        
        # 앞/뒤 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 2. 고품질 리사이징 (중간에 깨지지 않게 LANCZOS 사용)
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 제자리 중앙 배치
        canvas = Image.new("RGB", (w, h), (255, 255, 255))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 3. 프레임 시간(Duration)도 곡선에 맞춰 정밀 배분
    durations = []
    for i in range(total_frames):
        # 뒤로 갈수록 아주 미세하게 2ms씩 늘어나게 설계 (끊김 방지)
        d = 10 + int(100 * (i / total_frames)**3)
        durations.append(d)

    # 마지막 정지 화면 1.5초
    durations.append(1500)
    frames.append(frames[-1])

    # 4. 저장
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        optimize=True
    )
    print(f"✅ 자연스러운 회전 완성: {output_name}")

if __name__ == "__main__":
    create_smooth_stop_flip("H.png", "T.png")
