from PIL import Image, ImageDraw
import math
import os

def create_coin_pair(h_path, t_path):
    # 파일 존재 확인
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print(f"❌ 파일을 찾을 수 없습니다: {h_path} 또는 {t_path}")
        return

    def get_outer_clean(path):
        """외곽 배경만 선택적으로 제거하여 중앙 문자를 보호하는 로직"""
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # 0,0(좌측 상단)과 w-1,0(우측 상단)에서 시작해 연결된 배경만 투명화
        # thresh=50 정도로 높여서 지저분한 외곽 잔상을 확실히 제거
        ImageDraw.floodfill(img, xy=(0, 0), value=(0, 0, 0, 0), thresh=50)
        ImageDraw.floodfill(img, xy=(w-1, 0), value=(0, 0, 0, 0), thresh=50)
        ImageDraw.floodfill(img, xy=(0, h-1), value=(0, 0, 0, 0), thresh=50)
        ImageDraw.floodfill(img, xy=(w-1, h-1), value=(0, 0, 0, 0), thresh=50)
        return img

    print("🧹 배경 제거 및 이미지 최적화 중...")
    h_img_final = get_outer_clean(h_path)
    t_img_final = get_outer_clean(t_path)
    
    w, h = h_img_final.size
    total_frames = 120

    def generate_gif(final_side, filename):
        frames = []
        print(f"🎬 {filename} 렌더링 시작...")
        
        for i in range(total_frames):
            t = i / total_frames
            # 자연스러운 감속 곡선
            progress = 1 - (1 - t)**3
            
            # H결과는 20바퀴(7200도), T결과는 20.5바퀴(7380도)
            total_angle = 7200 if final_side == "H" else 7380
            angle = progress * total_angle
            
            rad = math.radians(angle)
            height_scale = abs(math.cos(rad))
            
            # 현재 각도에 따라 보여줄 이미지 선택
            current_face = t_img_final if 90 < (angle % 360) < 270 else h_img_final
            
            new_h = max(int(h * height_scale), 1)
            resized = current_face.resize((w, new_h), Image.Resampling.LANCZOS)
            
            # 투명 캔버스에 중앙 배치
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(resized, (0, (h - new_h) // 2), resized)
            frames.append(canvas)

        # 듀레이션 설정 (뒤로 갈수록 천천히)
        durations = [10 + int(250 * ((i/total_frames)**4)) for i in range(total_frames)]
        durations.append(2000) # 마지막 정지 화면 2초
        frames.append(frames[-1])

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, disposal=2, optimize=True)
        print(f"✅ {filename} 생성 완료!")

    # 결과물 2개 생성
    generate_gif("H", "result_H.gif")
    generate_gif("T", "result_T.gif")

if __name__ == "__main__":
    # 파일명이 정확한지 확인하세요!
    create_coin_pair("H.png", "T.png")
