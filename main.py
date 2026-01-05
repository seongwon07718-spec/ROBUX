from PIL import Image
import math
import os

def create_smooth_vertical_flip(h_path, t_path, output_name="coinflip_smooth.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    # 이미지 로드 및 고품질 변환
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 80프레임으로 대폭 늘려 끊김 현상 제거
    total_frames = 80 
    
    print("✨ 초고화질 렌더링 시작 (80 Frames)...")

    for i in range(total_frames):
        # 1. 자연스러운 감속을 위한 진행도 계산 (S-Curve 방식)
        t = i / total_frames
        # 부드러운 회전 각도 (마지막에 아주 천천히 멈춤)
        angle = (1 - (1 - t)**3) * 1440 
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        sin_val = math.sin(rad)
        
        # 2. 위아래 회전 및 원근감 수치 조절
        # 높이가 0이 될 때 앞뒤가 바뀌는 입체 연출
        height_scale = abs(cos_val)
        # 회전 시 크기 변화를 주어 원근감 극대화
        perspective = 1.0 + (0.12 * abs(sin_val)) 
        
        # 3. 부드러운 포물선 점프 (바운스)
        jump = 60 * (4 * t * (1 - t)) 
        
        # 앞/뒤 면 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 4. 고품질 리사이징 (LANCZOS 필터로 계단 현상 방지)
        new_w = int(w * perspective)
        new_h = max(int(h * height_scale * perspective), 1)
        resized = current_base.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 캔버스 배치 (여유 공간 확보)
        canvas_w, canvas_h = w + 60, h + 120
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        
        x_pos = (canvas_w - new_w) // 2
        y_pos = int((canvas_h - new_h) // 2 - jump)
        canvas.paste(resized, (x_pos, y_pos))
        frames.append(canvas)

    # 마지막 결과 고정 (2.5초)
    for _ in range(30):
        frames.append(frames[-1])

    # 5. 프레임 간격(duration) 미세 조정
    # 처음엔 초고속(12ms), 마지막엔 천천히 멈추도록 설정
    durations = []
    for i in range(total_frames):
        # 자연스러운 속도 변화 곡선 적용
        d = 12 + int(350 * (i / total_frames)**5)
        durations.append(d)
    durations.extend([2500] * 30)

    # 6. 최종 저장 (disposal=2로 잔상 완벽 제거)
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, disposal=2
    )
    print(f"✅ 자연스러운 GIF 저장 완료: {output_name}")

if __name__ == "__main__":
    create_smooth_vertical_flip("H.png", "T.png")
