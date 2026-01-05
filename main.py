from PIL import Image
import math
import os

def create_ultimate_smooth_gif(h_path, t_path, output_name="coinflip_ultra.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일을 찾을 수 없습니다.")
        return

    # 원본 로드
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 200프레임: 움짤이 가질 수 있는 물리적 한계치까지 생성
    total_frames = 200 
    
    print("💎 초고주사율 렌더링 중 (200 Frames)... 이 작업은 시간이 좀 걸릴 수 있습니다.")

    for i in range(total_frames):
        # 1. 큐빅 베지에(Cubic Bezier) 스타일의 부드러운 감속 곡선
        t = i / total_frames
        # 초반엔 폭발적으로 회전, 후반엔 아주 부드럽게 안착
        progress = 1 - (1 - t)**4 
        angle = progress * 2880 # 총 8바퀴 회전으로 속도감 극대화
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 수직 회전 (너비 고정, 높이만 정밀 조절)
        height_scale = abs(cos_val)
        
        # 면 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 3. 고품질 리사이징 및 캔버스 합성
        new_h = max(int(h * height_scale), 1)
        # Resampling.LANCZOS로 프레임 간 계단 현상 제거
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 결과 고정 프레임 (충분히 길게 3초)
    for _ in range(50):
        frames.append(frames[-1])

    # 4. 프레임 타이밍 조절 (ms 단위)
    durations = []
    for i in range(total_frames):
        if i < 100:
            # 초반 100프레임은 무조건 최속(10ms)으로 돌려 렉처럼 보이는 구간 삭제
            d = 10 
        else:
            # 후반 100프레임 동안 아주 세밀하게 속도를 늦춤 (드르륵 소리가 들리는 듯한 연출)
            ease_t = (i - 100) / 100
            d = 10 + int(600 * (ease_t**5)) # 5제곱 곡선으로 마지막에 아주 천천히 멈춤
        durations.append(d)
    durations.extend([3000] * 50)

    # 최종 저장 (disposal=2 필수: 프레임 찌꺼기 제거)
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, disposal=2
    )
    print(f"✅ 압도적 부드러움 완성: {output_name}")

if __name__ == "__main__":
    create_ultimate_smooth_gif("H.png", "T.png")
