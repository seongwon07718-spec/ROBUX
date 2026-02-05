import tkinter as tk
from tkinter import ttk, messagebox
import win32gui, win32api, win32con
import threading, time, random
from datetime import datetime

# --- SENTINAL 스타일 다크 디자인 ---
COLOR_BG = "#0F0F0F"
COLOR_CARD = "#1A1A1A"
COLOR_ACCENT = "#00FF41" # 네온 그린
COLOR_TEXT = "#FFFFFF"

running = False

def get_kakao_windows():
    """개선된 채팅방 찾기: 클래스명과 자식 창 구조를 모두 검사"""
    rooms = []
    def enum_cb(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # 카톡 메인창 및 관련 없는 창 제외
            if title and title not in ["카카오톡", "친구 관리", "설정", "알림", "더보기", "항목 목록"]:
                # 입력창(RichEdit)이 존재하는 창만 채팅방으로 간주
                if win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None) or \
                   win32gui.FindWindowEx(hwnd, None, "EVA_Window", None):
                    rooms.append(title)
    win32gui.EnumWindows(enum_cb, None)
    return list(set(rooms))

def add_log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_box.config(state="normal")
    log_box.insert(tk.END, f" > [{now}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def send_msg_logic():
    global running
    count = 0
    while running:
        room_name = combo_room.get()
        msg_raw = entry_msg.get("1.0", tk.END).strip()
        if not msg_raw:
            add_log("메시지를 입력하세요.")
            stop(); break
            
        msg_list = msg_raw.split('\n')
        msg = random.choice(msg_list)
        
        try:
            base_sec = float(entry_sec.get())
            actual_sec = base_sec * random.uniform(0.9, 1.1)
        except: actual_sec = 10

        hwnd = win32gui.FindWindow(None, room_name)
        if hwnd:
            # 비활성 입력을 위한 핸들 찾기
            hwndEdit = win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)
            if not hwndEdit: hwndEdit = win32gui.FindWindowEx(hwnd, None, "EVA_Window", None)
            
            if hwndEdit:
                win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, msg)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                win32api.PostMessage(hwndEdit, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                count += 1
                add_log(f"전송 성공 ({count}회): {msg[:10]}...")
        else:
            add_log("오류: 대상을 찾을 수 없음")
            stop(); break
        time.sleep(actual_sec)

def start():
    global running
    if not combo_room.get():
        messagebox.showwarning("경고", "목록에서 채팅방을 선택하세요.")
        return
    running = True
    btn_start.config(state="disabled", text="가동 중...", fg="#555")
    add_log("자동화 시스템 가동")
    threading.Thread(target=send_msg_logic, daemon=True).start()

def stop():
    global running
    running = False
    btn_start.config(state="normal", text="시스템 시작", fg=COLOR_ACCENT)
    add_log("시스템 중단")

def refresh():
    rooms = get_kakao_windows()
    combo_room['values'] = rooms
    if rooms:
        combo_room.current(0)
        add_log(f"동기화 성공: {len(rooms)}개 발견")
    else:
        add_log("발견된 채팅방 없음 (창을 열어주세요)")

# --- UI 레이아웃 ---
root = tk.Tk()
root.title("SENTINAL K-MACRO FINAL")
root.geometry("450x600")
root.configure(bg=COLOR_BG)
root.attributes("-topmost", True)

tk.Label(root, text="SENTINAL DASHBOARD", font=("Impact", 25), bg=COLOR_BG, fg=COLOR_ACCENT).pack(pady=20)

# 채팅방 선택
frame_target = tk.Frame(root, bg=COLOR_CARD, padx=15, pady=10)
frame_target.pack(fill="x", padx=20, pady=5)
tk.Label(frame_target, text="대상 채팅방 선택", bg=COLOR_CARD, fg="#888", font=("돋움", 9, "bold")).pack(anchor="w")
combo_room = ttk.Combobox(frame_target, width=38, state="readonly")
combo_room.pack(pady=10)
tk.Button(frame_target, text="목록 새로고침", command=refresh, bg="#333", fg="white", bd=0, padx=10).pack(anchor="e")

# 메시지 입력
frame_msg = tk.Frame(root, bg=COLOR_CARD, padx=15, pady=10)
frame_msg.pack(fill="x", padx=20, pady=5)
tk.Label(frame_msg, text="메시지 설정 (줄바꿈 시 랜덤 발송)", bg=COLOR_CARD, fg="#888", font=("돋움", 9, "bold")).pack(anchor="w")
entry_msg = tk.Text(frame_msg, width=40, height=5, bg="#000", fg=COLOR_ACCENT, bd=0, font=("Consolas", 10), insertbackground="white")
entry_msg.pack(pady=5)
entry_msg.insert("1.0", "메시지를 입력하세요.")

# 간격 설정
frame_cfg = tk.Frame(root, bg=COLOR_BG)
frame_cfg.pack(pady=10)
tk.Label(frame_cfg, text="발송 간격(초):", bg=COLOR_BG, fg="white").grid(row=0, column=0)
entry_sec = tk.Entry(frame_cfg, width=10, bg=COLOR_CARD, fg=COLOR_ACCENT, bd=0, justify="center")
entry_sec.insert(0, "10")
entry_sec.grid(row=0, column=1, padx=10)

# 실행 버튼
btn_start = tk.Button(root, text="시스템 시작", command=start, bg=COLOR_CARD, fg=COLOR_ACCENT, font=("돋움", 12, "bold"), width=33, bd=1, relief="flat")
btn_start.pack(pady=5)
tk.Button(root, text="긴급 중단", command=stop, bg="#222", fg="#FF4444", width=33, bd=0).pack()

# 로그창
log_box = tk.Text(root, height=8, width=55, state="disabled", font=("Consolas", 9), bg="#050505", fg=COLOR_ACCENT, bd=0)
log_box.pack(padx=20, pady=15)

refresh()
root.mainloop()
