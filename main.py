from PIL import Image, ImageDraw
import math
import os

def create_coin_pair(h_path, t_path):
    if not os.path.exists(h_path) or not os.path.exists(t_path):
        print("❌ H.png 또는 T.png 파일이 없습니다.")
        return

    def get_outer_clean(path):
        """외곽 배경만 선택적으로 제거하는 Flood Fill 로직"""
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # 좌측 상단 끝점(0,0)을 기준으로 연결된 배경만 투명화
        # 문자는 코인 안쪽에 고립되어 있으므로 지워지지 않음
        ImageDraw.floodfill(img, xy=(0, 0), value=(0, 0, 0, 0), thresh=30)
        ImageDraw.floodfill(img, xy=(w-1, 0), value=(0, 0, 0, 0), thresh=30)
        return img

    print("🧼 외곽 배경 정밀 제거 중 (문자 보호)...")
    h_img_final = get_outer_clean(h_path)
    t_img_final = get_clean_mask(t_path) if "get_clean_mask" in globals() else get_outer_clean(t_path)
    # 위 함수가 에러날 경우를 대비해 직접 호출로 통일
    t_img_final = get_outer_clean(t_path)
    
    w, h = h_img_final.size
    total_frames = 120

    def generate_gif(final_side, filename):
        frames = []
        print(f"🎬 {filename} 렌더링 시작...")
        
        for i in range(total_frames):
            t = i / total_frames
            progress = 1 - (1 - t)**3
            
            # 마지막에 지정된 면(final_side)이 나오도록 각도 계산
            # H가 결과면 7200도(짝수 바퀴), T가 결과면 7380도(홀수 바퀴 반)
            total_angle = 7200 if final_side == "H" else 7380
            angle = progress * total_angle
            
            rad = math.radians(angle)
            height_scale = abs(math.cos(rad))
            
            # 현재 회전 각도에 따른 면 결정
            current_face = t_img_final if 90 < (angle % 360) < 270 else h_img_final
            
            new_h = max(int(h * height_scale), 1)
            resized = current_face.resize((w, new_h), Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(resized, (0, (h - new_h) // 2), resized)
            frames.append(canvas)

        # 자연스러운 감속 타이밍
        durations = [15 + int(250 * ((i/total_frames)**3)) if i >= 80 else 10 for i in range(total_frames)]
        durations.append(2000)
        frames.append(frames[-1])

        frames[0].save(filename, format='GIF', save_all=True, append_images=frames[1:], 
                       duration=durations, loop=0, disposal=2, optimize=True)
        print(f"✅ {filename} 생성 완료!")

    # 2개의 파일 생성
    generate_gif("H", "result_H.gif")
    generate_gif("T", "result_T.gif")

if __name__ == "__main__":
    create_coin_pair("H.png", "T.png")
