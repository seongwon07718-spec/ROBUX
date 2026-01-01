import pyautogui
from pynput import mouse # pip install pynput

print("=== 좌표 추출기 시작 ===")
print("원하는 위치(수락 버튼 등)를 '클릭'하세요.")
print("종료하려면 이 창에서 Ctrl+C를 누르세요.")

def on_click(x, y, button, pressed):
    if pressed:
        # 클릭한 지점의 RGB 색상 가져오기
        color = pyautogui.pixel(int(x), int(y))
        print(f"📍 좌표: ({int(x)}, {int(y)}) | 색상(RGB): {color}")
        
        # 파일로 자동 저장 (나중에 복사해서 쓰기 편하게)
        with open("coords.txt", "a") as f:
            f.write(f"좌표: ({int(x)}, {int(y)}) | RGB: {color}\n")

with mouse.Listener(on_click=on_click) as listener:
    listener.join()
