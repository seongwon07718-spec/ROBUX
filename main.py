import tkinter as tk
from tkinter import ttk, messagebox
import win32gui, win32api, win32con
import threading, time, random
from datetime import datetime

# --- 디자인 설정 (SENTINAL 다크 모드) ---
BG_MAIN = "#0F0F0F"    # 메인 배경
BG_CARD = "#1A1A1A"    # 섹션 배경
POINT_COLOR = "#00FF41" # 네온 그린
TEXT_COLOR = "#FFFFFF"  # 흰색 글자
STOP_COLOR = "#FF4444"  # 중지 버튼 레드

running = False

def get_kakao_windows():
    """현재 열려 있는 모든 카카오톡 채팅방을 검색하여 리스트업"""
    rooms = []
    def enum_cb(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            classname = win32gui.GetClassName(hwnd)
            # 카톡 채팅방 특유의 클래스명(#32770) 또는 창 제목으로 필터링
            if title and title not in ["카카오톡", "친구 관리", "설정", "알림", "더보기"]:
                if classname == "#32770" or "RichEdit" in str(win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)):
                    rooms.append(title)
    win32gui.EnumWindows(enum_cb, None)
    return list(set(rooms))

def add_log(msg):
    """로그 출력 함수"""
    now = datetime.now().strftime('%H:%M:%S')
    log_box.config(state="normal")
    log_box.insert(tk.END, f" > [{now}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def send_msg_logic():
    """비활성 발송 핵심 로직"""
    global running
    count = 0
    while running:
        room_name = combo_room.get()
        msg_raw = entry_msg.get("1.0", tk.END).strip()
        if not msg_raw: 
            add_log("메시지를 입력해주세요.")
            stop()
            break
            
        msg_list = msg_raw.split('\n')
        msg = random.choice(msg_list) # 여러 줄 입력 시 랜덤 발송
        
        try:
            base_sec = float(entry_sec.get())
            actual_sec = base_sec * random.uniform(0.9, 1.1) # 10% 오차 랜덤 지연
        except: actual_sec = 10

        hwnd = win32gui.FindWindow(None, room_name)
        if hwnd:
            # 입력창 찾기 (버전에 따라 다를 수 있음)
            hwndEdit = win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)
            if not hwndEdit: hwndEdit = win32gui.FindWindowEx(hwnd, None, "EVA_Window", None)
            
            if hwndEdit:
                win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, msg)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                count += 1
                add_log(f"전송 성공 ({count}회): {msg[:15]}")
            else:
                add_log("오류: 입력창을 찾을 수 없습니다.")
        else:
            add_log("오류: 채팅방 창이 닫혀있습니다.")
            stop()
            break
        time.sleep(actual_sec)

def start():
    global running
    if not combo_room.get():
        messagebox.showwarning("경고", "대상을 선택하고 '목록 새로고침'을 눌러주세요.")
        return
    running = True
    btn_start.config(state="disabled", text="작동 중...", fg="#555")
    add_log("시스템 가동 시작")
    threading.Thread(target=send_msg_logic, daemon=True).start()

def stop():
    global running
    running = False
    btn_start.config(state="normal", text="시스템 시작", fg=POINT_COLOR)
    add_log("시스템 중단됨.")

def refresh():
    rooms = get_kakao_windows()
    combo_room.config(values=rooms)
    if rooms: combo_room.current(0)
    add_log(f"채팅방 목록 동기화 완료 ({len(rooms)}개)")

# --- GUI 구성 ---
root = tk.Tk()
root.title("SENTINAL K-MACRO FINAL")
root.geometry("450x650")
root.configure(bg=BG_MAIN)
root.attributes("-topmost", True) # 항상 위

# 타이틀 바
tk.Label(root, text="SENTINAL DASHBOARD", font=("Impact", 22), bg=BG_MAIN, fg=POINT_COLOR).pack(pady=20)

# 1. 채팅방 선택 섹션
frame_1 = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
frame_1.pack(fill="x", padx=20, pady=5)
tk.Label(frame_1, text="대상 채팅방 선택", font=("돋움", 9, "bold"), bg=BG_CARD, fg="#AAA").pack(anchor="w")
combo_room = ttk.Combobox(frame_1, width=38, state="readonly")
combo_room.pack(pady=8)
tk.Button(frame_1, text="목록 새로고침", command=refresh, bg="#333", fg="white", bd=0, padx=15).pack(anchor="e")

# 2. 메시지 설정 섹션
frame_2 = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
frame_2.pack(fill="x", padx=20, pady=5)
tk.Label(frame_2, text="메시지 입력 (한 줄에 하나씩)", font=("돋움", 9, "bold"), bg=BG_CARD, fg="#AAA").pack(anchor="w")
entry_msg = tk.Text(frame_2, width=40, height=5, bg="#000", fg=POINT_COLOR, insertbackground="white", bd=0, font=("Consolas", 10))
entry_msg.pack(pady=5)
entry_msg.insert("1.0", "테스트 메시지 1\n테스트 메시지 2")

# 3. 간격 설정 섹션
frame_3 = tk.Frame(root, bg=BG_MAIN)
frame_3.pack(pady=15)
tk.Label(frame_3, text="발송 간격(초):", bg=BG_MAIN, fg="white").grid(row=0, column=0)
entry_sec = tk.Entry(frame_3, width=8, bg=BG_CARD, fg=POINT_COLOR, bd=0, justify="center")
entry_sec.insert(0, "10")
entry_sec.grid(row=0, column=1, padx=10)

# 4. 제어 버튼
btn_start = tk.Button(root, text="시스템 시작", command=start, bg=BG_CARD, fg=POINT_COLOR, font=("돋움", 12, "bold"), width=32, bd=1, relief="flat")
btn_start.pack(pady=5)
tk.Button(root, text="긴급 중단", command=stop, bg="#222", fg=STOP_COLOR, width=32, bd=0).pack()

# 5. 로그 창
tk.Label(root, text="실시간 활동 로그", font=("돋움", 8), bg=BG_MAIN, fg="#888").pack(pady=(15,0))
log_box = tk.Text(root, height=10, width=55, state="disabled", font=("Consolas", 9), bg="#050505", fg=POINT_COLOR, bd=0)
log_box.pack(padx=20, pady=5)

refresh()
root.mainloop()
