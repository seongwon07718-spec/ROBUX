import tkinter as tk
from tkinter import ttk, messagebox
import win32gui, win32api, win32con
import threading, time, random, pyautogui
from datetime import datetime

# --- SENTINAL 스타일 디자인 ---
BG_MAIN = "#0F0F0F"
BG_CARD = "#1A1A1A"
COLOR_ACCENT = "#00FF41" 
COLOR_TEXT = "#FFFFFF"

running = False
target_rooms = {} # {hwnd: title}

def add_log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_box.config(state="normal")
    log_box.insert(tk.END, f" > [{now}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def select_window_task():
    """마우스 클릭 위치의 창을 가져오는 로직"""
    add_log("3초 후 마우스가 위치한 창을 인식합니다...")
    add_log("대상 카톡창을 클릭하거나 마우스를 올려두세요.")
    
    # 카운트다운 동안 프로그램 창을 잠시 숨김 (선택 편의성)
    root.withdraw() 
    time.sleep(3)
    
    # 마우스 현재 위치의 창 핸들(HWND) 가져오기
    x, y = pyautogui.position()
    hwnd = win32gui.WindowFromPoint((x, y))
    
    # 클릭한 곳이 채팅창 내부(자식 창)일 수 있으므로 최상위 부모창을 찾음
    while win32gui.GetParent(hwnd):
        hwnd = win32gui.GetParent(hwnd)
    
    title = win32gui.GetWindowText(hwnd)
    
    if title and title not in ["", "카카오톡", "Program Manager"]:
        if hwnd not in target_rooms:
            target_rooms[hwnd] = title
            listbox_rooms.insert(tk.END, f" {title}")
            add_log(f"등록 완료: {title}")
        else:
            add_log("이미 등록된 창입니다.")
    else:
        add_log("오류: 유효한 창을 찾지 못했습니다.")
    
    root.deiconify() # 다시 프로그램 표시

def send_msg_logic():
    global running
    while running:
        if not target_rooms:
            add_log("발송 대상이 없습니다.")
            stop(); break
            
        msg_list = entry_msg.get("1.0", tk.END).strip().split('\n')
        try: delay = float(entry_sec.get())
        except: delay = 10

        for hwnd, title in list(target_rooms.items()):
            if not running: break
            
            if win32gui.IsWindow(hwnd):
                msg = random.choice(msg_list)
                # 입력창 핸들(RichEdit) 검색
                hwndEdit = win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)
                if not hwndEdit: hwndEdit = win32gui.FindWindowEx(hwnd, None, "EVA_Window", None)
                
                if hwndEdit:
                    win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, msg)
                    win32api.PostMessage(hwndEdit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                    win32api.PostMessage(hwndEdit, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                    add_log(f"[{title}] 발송 성공")
            else:
                add_log(f"[{title}] 창이 닫혀있어 제외합니다.")
                del target_rooms[hwnd]
        
        time.sleep(delay * random.uniform(0.9, 1.1))

def start():
    global running
    if not target_rooms:
        messagebox.showwarning("경고", "창 추가 버튼으로 채팅방을 먼저 등록하세요.")
        return
    running = True
    btn_start.config(state="disabled", text="가동 중...", bg="#333")
    add_log("멀티 발송 시스템 가동")
    threading.Thread(target=send_msg_logic, daemon=True).start()

def stop():
    global running
    running = False
    btn_start.config(state="normal", text="시스템 가동", bg=BG_CARD)
    add_log("시스템 중단")

def clear_list():
    target_rooms.clear()
    listbox_rooms.delete(0, tk.END)
    add_log("목록 초기화")

# --- GUI 구성 ---
root = tk.Tk()
root.title("SENTINAL MULTI-SENDER")
root.geometry("450x700")
root.configure(bg=BG_MAIN)

tk.Label(root, text="SENTINAL DASHBOARD", font=("Impact", 25), bg=BG_MAIN, fg=COLOR_ACCENT).pack(pady=20)

frame_list = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
frame_list.pack(fill="x", padx=20, pady=5)
tk.Label(frame_list, text="발송 대상 목록", font=("돋움", 9), bg=BG_CARD, fg="#888").pack(anchor="w")
listbox_rooms = tk.Listbox(frame_list, height=5, bg="#000", fg=COLOR_TEXT, bd=0)
listbox_rooms.pack(fill="x", pady=10)

btn_f = tk.Frame(frame_list, bg=BG_CARD)
btn_f.pack(fill="x")
tk.Button(btn_f, text=" 직접 창 클릭해서 추가 ", command=lambda: threading.Thread(target=select_window_task).start(), 
          bg=COLOR_ACCENT, fg="#000", font=("돋움", 9, "bold"), bd=0).pack(side="left", expand=True, fill="x", padx=2)
tk.Button(btn_f, text="초기화", command=clear_list, bg="#333", fg="white", bd=0).pack(side="left", expand=True, fill="x", padx=2)

frame_msg = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
frame_msg.pack(fill="x", padx=20, pady=5)
tk.Label(frame_msg, text="메시지 내용 (한 줄에 하나씩)", font=("돋움", 9), bg=BG_CARD, fg="#888").pack(anchor="w")
entry_msg = tk.Text(frame_msg, width=40, height=5, bg="#000", fg=COLOR_ACCENT, bd=0, font=("Consolas", 10))
entry_msg.pack(pady=5)
entry_msg.insert("1.0", "안녕하세요\n반갑습니다")

frame_cfg = tk.Frame(root, bg=BG_MAIN)
frame_cfg.pack(pady=10)
tk.Label(frame_cfg, text="발송 주기(초):", bg=BG_MAIN, fg="white").grid(row=0, column=0)
entry_sec = tk.Entry(frame_cfg, width=10, bg=BG_CARD, fg=COLOR_ACCENT, bd=0, justify="center"); entry_sec.insert(0, "10"); entry_sec.grid(row=0, column=1, padx=10)

btn_start = tk.Button(root, text="시스템 가동", command=start, bg=BG_CARD, fg=COLOR_ACCENT, font=("돋움", 12, "bold"), width=33, bd=1, relief="flat")
btn_start.pack(pady=5)
tk.Button(root, text="긴급 중단", command=stop, bg="#222", fg="#FF4444", width=33, bd=0).pack()

log_box = tk.Text(root, height=10, width=55, state="disabled", font=("Consolas", 9), bg="#050505", fg=COLOR_ACCENT, bd=0)
log_box.pack(padx=20, pady=15)

root.mainloop()
