from PIL import Image, ImageOps
import math
import os

def create_pro_clean_flip(h_path, t_path, output_name="coin_pro_300.gif"):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    def get_clean_image(path):
        # 이미지를 열고 RGBA 모드로 변환
        img = Image.open(path).convert("RGBA")
        datas = img.getdata()
        
        # 문자를 보호하기 위해 배경색(보통 좌측 상단 끝 픽셀)을 추출
        bg_color = datas[0]
        
        new_data = []
        for item in datas:
            # 배경색과 유사한 색상만 투명하게 처리 (문자 보호를 위해 오차 범위 최소화)
            # 배경이 순백색(255, 255, 255)이거나 특정 색일 때만 투명화
            if item[0] == bg_color[0] and item[1] == bg_color[1] and item[2] == bg_color[2]:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        return img

    # 1. 배경 제거 로직 적용 (H, T 동일하게 처리)
    print("🧹 이미지 배경 정밀 제거 중...")
    h_img = get_clean_image(h_path)
    t_img = get_clean_image(t_path)
    w, h = h_img.size
    
    frames = []
    total_frames = 300 # 요청하신 300프레임
    
    print(f"🎬 300프레임 렌더링 시작 (속도 유지)...")

    for i in range(total_frames):
        t = i / total_frames
        
        # 속도 곡선 (사용자님이 만족하셨던 그 속도감 유지)
        progress = 1 - (1 - t)**3
        angle = progress * 7200 # 20바퀴 광속 회전
        
        rad = math.radians(angle)
        height_scale = abs(math.cos(rad))
        
        # 앞/뒤 면 결정
        current_base = t_img if 90 < (angle % 360) < 270 else h_img
        
        # 2. 수직 회전 리사이즈
        new_h = max(int(h * height_scale), 1)
        resized = current_base.resize((w, new_h), Image.Resampling.LANCZOS)
        
        # 3. 투명 캔버스에 합성
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        y_pos = (h - new_h) // 2
        canvas.paste(resized, (0, y_pos), resized) # 마스크 사용으로 투명도 완벽 유지
        frames.append(canvas)

    # 4. 프레임 시간(Duration) 설계 (7초 안팎 유지)
    durations = []
    for i in range(total_frames):
        if i < 200:
            d = 10 # 광속 구간
        else:
            # 부드러운 감속 구간
            ease_t = (i - 200) / 100
            d = 10 + int(300 * (ease_t**4))
        durations.append(d)

    # 정지 화면 2초
    durations.append(2000)
    frames.append(frames[-1])

    # 5. 저장 (disposal=2 필수: 배경이 겹치지 않게 함)
    print("💾 저장 중... (300프레임이라 시간이 조금 걸립니다)")
    frames[0].save(
        output_name, format='GIF', save_all=True,
        append_images=frames[1:], duration=durations, loop=0, 
        disposal=2, optimize=True
    )
    print(f"✅ 완성: {output_name}")

if __name__ == "__main__":
    create_pro_clean_flip("H.png", "T.png")
