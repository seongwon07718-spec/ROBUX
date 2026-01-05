from PIL import Image
import math
import os

def create_bloxluck_gif(h_path, t_path, output_name="coinflip.gif"):
    # 1. 원본 이미지 불러오기
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print(f"❌ 에러: {h_path} 또는 {t_path} 파일이 없습니다!")
        return

    h_img = Image.open(h_path).convert("RGBA")
    t_img = Image.open(t_path).convert("RGBA")
    w, h = h_img.size
    
    frames = []
    # 총 30프레임으로 더 부드럽게 연출
    total_rotation_frames = 30
    
    print("⏳ GIF 생성 중... (Bloxluck 스타일 감속 적용)")

    for i in range(total_rotation_frames):
        # 3D 회전 효과: 0도에서 약 1080도(3바퀴)까지 회전
        angle = i * 45 
        rad = math.radians(angle)
        
        # 코사인 함수를 이용해 가로 너비를 1에서 0으로 줄여 3D 느낌 구현
        width_scale = abs(math.cos(rad))
        
        # 각도에 따라 앞면/뒷면 결정
        if (angle % 360) > 90 and (angle % 360) < 270:
            current_base = t_img
        else:
            current_base = h_img
            
        # 가로 길이 조절 및 중앙 배치
        new_w = max(int(w * width_scale), 1)
        resized = current_base.resize((new_w, h), Image.Resampling.LANCZOS)
        
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(resized, ((w - new_w) // 2, 0))
        frames.append(canvas)

    # 마지막 결과 프레임 (멈춤 효과용)
    # 여기서는 '앞면'으로 끝나는 GIF를 만듭니다. (뒷면을 원하면 t_img로 변경)
    for _ in range(15):
        frames.append(h_img)

    # 2. Bloxluck 스타일 감속 Duration 설정 (단위: ms)
    # 20ms(초고속) -> 마지막 400ms(느림) -> 2000ms(정지)
    durations = []
    for i in range(total_rotation_frames):
        if i < 15: durations.append(20)      # 가속 구간
        elif i < 22: durations.append(50)     # 보통 구간
        elif i < 27: durations.append(150)    # 감속 구간
        else: durations.append(400)           # 멈추기 직전
    
    durations.extend([2000] * 15) # 결과 노출 시간 (2초)

    # 3. 파일 저장
    frames[0].save(
        output_name,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        transparency=0,
        disposal=2 # 프레임 잔상 방지
    )
    print(f"✅ 생성 완료! 파일명: {output_name}")

# 실행부
if __name__ == "__main__":
    create_bloxluck_gif("H.png", "T.png")
