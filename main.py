from PIL import Image
import math
import os

def create_insane_2000frame_gif(h_path, t_path, output_name="coinflip_2000.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ 파일이 없습니다.")
        return

    # 이미지 로드
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 요청하신 2000프레임 설정 (용량이 커질 수 있으니 주의하세요!)
    total_frames = 2000 
    
    print(f"🔥 2000프레임 렌더링 시작... 압도적인 부드러움을 생성 중입니다.")

    for i in range(total_frames):
        # 1. 진행도 계산 (후반부에만 살짝 느려지게 세팅)
        t = i / total_frames
        # 초반 80%까지는 거의 일정하게 광속 회전, 마지막 20%에서만 감속
        if t < 0.8:
            progress = t 
        else:
            # 마지막 구간에서 부드럽게 안착하는 곡선
            sub_t = (t - 0.8) / 0.2
            progress = 0.8 + (0.2 * (1 - (1 - sub_t)**3))
            
        angle = progress * 7200 # 총 20바퀴 회전 (속도감 극대화)
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 선명도 유지 (블러 제거) 및 수직 회전
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        # 선명한 화질을 위해 LANCZOS 유지
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 제자리 고정 캔버스
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 결과 고정 (마지막 정지 화면은 깔끔하게 2초)
    for _ in range(50):
        frames.append(frames[-1])

    # 4. 프레임 타이밍 (처 느린 느낌 삭제)
    durations = []
    for i in range(total_frames):
        # 1600프레임까지는 2ms(인간의 눈으로 인지 불가능한 속도)
        if i < 1600:
            d = 2 
        else:
            # 마지막 400프레임에서만 2ms -> 50ms로 짧게 감속
            ease_t = (i - 1600) / 400
            d = 2 + int(48 * (ease_t**2))
        durations.append(d)
    durations.extend([2000] * 50)

    # 5. 저장 (용량 최적화를 위해 optimize 사용)
    print("💾 파일 저장 중... (프레임이 많아 시간이 걸립니다)")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 극한의 2000프레임 완성: {output_name}")

if __name__ == "__main__":
    create_insane_2000frame_gif("H.png", "T.png")
