from PIL import Image
import math
import os

def create_bg_jump_flip(h_path, t_path, bg_path, output_name="coin_final_bg.gif"):
    if not all(os.path.exists(p) for p in [h_path, t_path, bg_path]):
        print("❌ 파일(H, T, 배경) 중 없는 것이 있습니다.")
        return

    # 1. 이미지 로드
    bg_img = Image.open(bg_path).convert("RGBA")
    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    bg_w, bg_h = bg_img.size
    
    frames = []
    total_frames = 150 # 7초 내외의 부드러운 연출
    
    # 코인 크기 조절 (배경에 맞춰 원본의 60%로 축소)
    coin_scale = 0.6
    c_w = int(h_img.size[0] * coin_scale)
    c_h = int(h_img.size[1] * coin_scale)
    h_img = h_img.resize((c_w, c_h), Image.Resampling.LANCZOS)
    t_img = t_img.resize((c_w, c_h), Image.Resampling.LANCZOS)

    print("🎨 배경 합성 및 낙하 연출 렌더링 중...")

    for i in range(total_frames):
        t = i / total_frames
        
        # 2. 물리 연출: 위에서 떨어지는 궤적
        # 처음엔 화면 밖 위(negative y)에서 시작해 중앙으로 낙하
        if t < 0.5:
            # 0~0.5초: 낙하 구간 (물리적으로 가속)
            fall_t = t / 0.5
            y_pos = int(-c_h + (bg_h/2 + c_h) * (fall_t**2))
        else:
            # 0.5~1.0초: 제자리 안착 및 미세 바운스
            y_pos = int(bg_h/2)

        # 3. 회전 연출: 초반 광속 -> 후반 급감속
        # progress가 1에 가까워질수록 속도가 0이 됨
        progress = 1 - (1 - t)**4
        angle = progress * 7200 # 20바퀴 광속 회전
        
        rad = math.radians(angle)
        height_scale = abs(math.cos(rad))
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 수직 회전 리사이즈
        new_h = max(int(c_h * height_scale), 1)
        resized_coin = current_base.resize((c_w, new_h), Image.Resampling.LANCZOS)
        
        # 4. 배경 위에 코인 합성
        frame = bg_img.copy()
        coin_x = (bg_w - c_w) // 2
        coin_y = y_pos - (new_h // 2)
        
        # 배경 중앙 부근에 코인 부착
        frame.paste(resized_coin, (coin_x, int(coin_y)), resized_coin)
        frames.append(frame)

    # 5. 프레임 타이밍: 처음엔 10ms로 광속, 마지막엔 틱!
    durations = []
    for i in range(total_frames):
        if i < 100:
            d = 10
        else:
            ease_t = (i - 100) / 50
            d = 10 + int(300 * (ease_t**4))
        durations.append(d)

    # 정지 화면 2초
    durations.append(2000)
    frames.append(frames[-1])

    # 6. 저장
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        optimize=True
    )
    print(f"✅ 배경 합성 완료: {output_name}")

if __name__ == "__main__":
    # 파일명이 background.png 인지 확인하세요
    create_bg_jump_flip("H.png", "T.png", "background.png")
