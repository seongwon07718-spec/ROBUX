from PIL import Image
import math
import os

def create_perfect_5s_gif(h_path, t_path, output_name="coinflip_5s.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ 파일이 없습니다.")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 2000프레임으로 5초를 쪼개서 부드러움의 극한을 구현
    total_frames = 2000 
    
    print("🔥 5초 고정 연출 렌더링 중... (2000 Frames)")

    for i in range(total_frames):
        # 1. 5초 동안의 회전 로직 (처음엔 미친듯이 빠르다가 나중에 부드럽게)
        t = i / total_frames
        # 지수 감속 곡선: 처음엔 7200도(20바퀴)를 순식간에 돌고 마지막에 안착
        progress = 1 - (1 - t)**4 
        angle = progress * 7200 
        
        rad = math.radians(angle)
        cos_val = math.cos(rad)
        
        # 2. 위아래 회전 (선명도 100% 유지)
        height_scale = abs(cos_val)
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 제자리 고정 캔버스 (흔들림 제거)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos))
        frames.append(canvas)

    # 4. 정밀한 5초 타이밍 설계 (ms 단위)
    # 총 5000ms를 2000프레임에 나눠 담음
    durations = []
    remaining_time = 5000 # 5초 (ms)
    
    for i in range(total_frames):
        # 초반 1500프레임까지는 1ms~2ms로 초광속 재생 (렉 제거)
        if i < 1500:
            d = 1 
        else:
            # 나머지 500프레임 동안 남은 시간을 지수적으로 분배 (드르륵 멈춤)
            ease_t = (i - 1500) / 500
            d = 1 + int(150 * (ease_t**5)) # 마지막엔 한 프레임당 0.15초까지 느려짐
        
        durations.append(d)
        remaining_time -= d

    # 마지막 정지 화면은 별도로 3초 추가 (결과 확인용)
    durations.extend([3000] * 50)
    for _ in range(50):
        frames.append(frames[-1])

    # 5. 저장
    print("💾 저장 중... 용량이 크니 잠시만 기다려주세요.")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 5초의 기적 완성: {output_name}")

if __name__ == "__main__":
    create_perfect_5s_gif("H.png", "T.png")
