import tkinter as tk
from tkinter import ttk, messagebox
import win32gui, win32api, win32con
import threading, time, random, pyautogui
from datetime import datetime

# --- 디자인 설정 ---
BG_MAIN, BG_CARD = "#0F0F0F", "#1A1A1A"
ACCENT, TEXT_COLOR, STOP_COLOR = "#00FF41", "#FFFFFF", "#FF4444"

running = False
target_rooms = {} 

def add_log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    log_box.config(state="normal")
    log_box.insert(tk.END, f" > [{now}] {msg}\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def select_window_task():
    """사용자가 클릭한 창의 정확한 핸들을 획득"""
    add_log("3초 후 마우스 아래의 창을 타겟팅합니다...")
    root.iconify()
    time.sleep(3)
    
    x, y = pyautogui.position()
    hwnd = win32gui.WindowFromPoint((x, y))
    
    # 최상위 부모 창 찾기
    while win32gui.GetParent(hwnd):
        hwnd = win32gui.GetParent(hwnd)
    
    title = win32gui.GetWindowText(hwnd)
    if title and title not in ["", "카카오톡", "Program Manager"]:
        if hwnd not in target_rooms:
            target_rooms[hwnd] = title
            listbox_rooms.insert(tk.END, f" {title}")
            add_log(f"타겟 등록 완료: {title}")
        else: add_log("이미 등록된 창입니다.")
    else: add_log("오류: 유효한 창을 클릭해주세요.")
    root.deiconify()

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
                
                # 입력창(RichEdit)을 찾는 더 강력한 로직
                hwnd_edit = win32gui.FindWindowEx(hwnd, None, "RichEdit20W", None)
                if not hwnd_edit:
                    hwnd_edit = win32gui.FindWindowEx(hwnd, None, "EVA_Window", None)
                
                if hwnd_edit:
                    # 1. 창을 활성화 시키지 않고 텍스트 밀어넣기
                    win32gui.SendMessage(hwnd_edit, win32con.WM_SETTEXT, 0, msg)
                    time.sleep(0.2) # 데이터 처리 시간 확보
                    
                    # 2. 엔터키 전송 (KEYDOWN/UP 세트)
                    win32api.PostMessage(hwnd_edit, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                    time.sleep(0.1)
                    win32api.PostMessage(hwnd_edit, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                    
                    add_log(f"[{title}] 메시지 전송 성공")
                else:
                    add_log(f"[{title}] 입력창 탐색 실패")
            else:
                add_log(f"[{title}] 창이 닫힘. 제거합니다.")
                del target_rooms[hwnd]
        
        time.sleep(delay * random.uniform(0.9, 1.1))

def start():
    global running
    if not target_rooms: return
    running = True
    btn_start.config(state="disabled", text="시스템 가동 중", bg="#333")
    add_log("자동화 프로세스 시작")
    threading.Thread(target=send_msg_logic, daemon=True).start()

def stop():
    global running
    running = False
    btn_start.config(state="normal", text="시스템 가동", bg=BG_CARD)
    add_log("프로세스 중단됨")

# --- GUI 구성 ---
root = tk.Tk()
root.title("SENTINAL FINAL V3")
root.geometry("450x680")
root.configure(bg=BG_MAIN)
root.attributes("-topmost", True)

tk.Label(root, text="SENTINAL DASHBOARD", font=("Impact", 25), bg=BG_MAIN, fg=ACCENT).pack(pady=20)

f1 = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
f1.pack(fill="x", padx=20, pady=5)
tk.Label(f1, text="대상 목록 (멀티 발송 가능)", font=("돋움", 9), bg=BG_CARD, fg="#888").pack(anchor="w")
listbox_rooms = tk.Listbox(f1, height=5, bg="#000", fg=TEXT_COLOR, bd=0, font=("돋움", 10))
listbox_rooms.pack(fill="x", pady=10)
tk.Button(f1, text=" 직접 창 클릭해서 추가 ", command=lambda: threading.Thread(target=select_window_task).start(), bg=ACCENT, fg="#000", font=("돋움", 9, "bold"), bd=0).pack(fill="x")

f2 = tk.Frame(root, bg=BG_CARD, padx=15, pady=10)
f2.pack(fill="x", padx=20, pady=5)
tk.Label(f2, text="메시지 내용 (줄바꿈 시 랜덤)", font=("돋움", 9), bg=BG_CARD, fg="#888").pack(anchor="w")
entry_msg = tk.Text(f2, width=40, height=5, bg="#000", fg=ACCENT, bd=0, font=("Consolas", 10), insertbackground="white"); entry_msg.pack(pady=5)
entry_msg.insert("1.0", "발송 테스트입니다")

f3 = tk.Frame(root, bg=BG_MAIN)
f3.pack(pady=10)
tk.Label(f3, text="간격(초):", bg=BG_MAIN, fg="white").grid(row=0, column=0)
entry_sec = tk.Entry(f3, width=10, bg=BG_CARD, fg=ACCENT, bd=0, justify="center"); entry_sec.insert(0, "10"); entry_sec.grid(row=0, column=1, padx=10)

btn_start = tk.Button(root, text="시스템 가동", command=start, bg=BG_CARD, fg=ACCENT, font=("돋움", 12, "bold"), width=33, bd=1, relief="flat")
btn_start.pack(pady=5)
tk.Button(root, text="초기화/중단", command=stop, bg="#222", fg=STOP_COLOR, width=33, bd=0).pack()

log_box = tk.Text(root, height=10, width=55, state="disabled", font=("Consolas", 9), bg="#050505", fg=ACCENT, bd=0)
log_box.pack(padx=20, pady=15)

root.mainloop()
