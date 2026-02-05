import tkinter as tk
from tkinter import ttk, messagebox
import win32gui, win32api, win32con
import threading, time, random
from datetime import datetime

# --- 설정 및 스타일 ---
BG_COLOR = "#1e1e1e"  # 배경색
FG_COLOR = "#ffffff"  # 글자색
ACCENT_COLOR = "#3d3d3d" # 입력창 색상
BTN_START = "#2ecc71" # 시작 버튼
BTN_STOP = "#e74c3c"  # 중지 버튼

running = False

def get_kakao_windows():
    rooms = []
    def enum_cb(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            classname = win32gui.GetClassName(hwnd)
            if classname == "#32770" and title and title not in ["카카오톡", "친구 관리", "설정", "알림"]:
                rooms.append(title)
    win32gui.EnumWindows(enum_cb, None)
    return list(set(rooms))

def add_log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_box.config(state="normal")
    log_box.insert(tk.END, f"[{now}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def send_msg_logic():
    global running
    count = 0
    try: limit = int(entry_limit.get())
    except: limit = 0

    while running:
        room_name = combo_room.get()
        msg_list = entry_msg.get("1.0", tk.END).strip().split('\n')
        if not msg_list or msg_list == ['']: break
        msg = random.choice(msg_list)
        
        try:
            base_sec = float(entry_sec.get())
            actual_sec = base_sec * random.uniform(0.85, 1.15)
        except: actual_sec = 10

        hwnd = win32gui.FindWindow(None, room_name)
        if hwnd:
            hwndEdit = win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)
            if not hwndEdit: hwndEdit = win32gui.FindWindowEx(hwnd, None, "EVA_Window", None)
            
            if hwndEdit:
                win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, msg)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                count += 1
                add_log(f"전송 성공: {msg[:12]}...")
                if limit > 0 and count >= limit:
                    add_log("목표 횟수 도달 완료")
                    stop(); break
        else:
            add_log("창 찾기 실패. 중단합니다.")
            stop(); break
        time.sleep(actual_sec)

def start():
    global running
    if not combo_room.get():
        messagebox.showwarning("Warning", "대상 채팅방을 선택하세요.")
        return
    running = True
    btn_start.config(state="disabled", bg="#555555")
    btn_stop.config(state="normal", bg=BTN_STOP)
    add_log("매크로 프로세스 시작")
    threading.Thread(target=send_msg_logic, daemon=True).start()

def stop():
    global running
    running = False
    btn_start.config(state="normal", bg=BTN_START)
    btn_stop.config(state="disabled", bg="#555555")
    add_log("매크로 프로세스 중단")

# --- GUI 레이아웃 ---
root = tk.Tk()
root.title("SENTINAL Style Macro")
root.geometry("420x580")
root.configure(bg=BG_COLOR)
root.attributes("-topmost", True)

style = ttk.Style()
style.theme_use('clam')
style.configure("TCombobox", fieldbackground=ACCENT_COLOR, background=ACCENT_COLOR, foreground=FG_COLOR)

# 타이틀
tk.Label(root, text="DASHBOARD", font=("Impact", 20), bg=BG_COLOR, fg=BTN_START).pack(pady=15)

# 1. 채팅방 선택
tk.Label(root, text="TARGET CHATROOM", font=("Arial", 9, "bold"), bg=BG_COLOR, fg="#888888").pack()
frame_room = tk.Frame(root, bg=BG_COLOR)
frame_room.pack(pady=5)
combo_room = ttk.Combobox(frame_room, width=35, state="readonly")
combo_room.pack(side="left", padx=5)
tk.Button(frame_room, text="REFRESH", command=lambda: combo_room.config(values=get_kakao_windows()), 
          bg=ACCENT_COLOR, fg=FG_COLOR, bd=0).pack(side="left")

# 2. 메시지 입력
tk.Label(root, text="MESSAGE (RANDOM PICK)", font=("Arial", 9, "bold"), bg=BG_COLOR, fg="#888888").pack(pady=5)
entry_msg = tk.Text(root, width=45, height=5, bg=ACCENT_COLOR, fg=FG_COLOR, insertbackground="white", bd=0)
entry_msg.pack(padx=20)
entry_msg.insert("1.0", "매크로 테스트 메시지\n안녕하세요 반갑습니다\n자동 발송 중입니다")

# 3. 설정
frame_set = tk.Frame(root, bg=BG_COLOR)
frame_set.pack(pady=15)
tk.Label(frame_set, text="INTERVAL(S)", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, padx=5)
entry_sec = tk.Entry(frame_set, width=8, bg=ACCENT_COLOR, fg=FG_COLOR, bd=0, justify="center"); entry_sec.insert(0, "10"); entry_sec.grid(row=0, column=1, padx=5)
tk.Label(frame_set, text="LIMIT", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=2, padx=5)
entry_limit = tk.Entry(frame_set, width=8, bg=ACCENT_COLOR, fg=FG_COLOR, bd=0, justify="center"); entry_limit.insert(0, "0"); entry_limit.grid(row=0, column=3, padx=5)

# 4. 버튼
btn_start = tk.Button(root, text="START AUTOMATION", command=start, bg=BTN_START, fg="white", font=("Arial", 10, "bold"), width=35, height=2, bd=0)
btn_start.pack(pady=5)
btn_stop = tk.Button(root, text="STOP", command=stop, bg="#555555", fg="white", font=("Arial", 10, "bold"), width=35, bd=0, state="disabled")
btn_stop.pack()

# 5. 로그
tk.Label(root, text="ACTIVITY LOG", font=("Arial", 8), bg=BG_COLOR, fg="#888888").pack(pady=5)
log_box = tk.Text(root, height=10, width=50, state="disabled", font=("Consolas", 9), bg="#121212", fg="#00ff00", bd=0)
log_box.pack(padx=10, pady=5)

combo_room.config(values=get_kakao_windows())
root.mainloop()
