import tkinter as tk
from tkinter import ttk

def on_click():
    print("버튼이 클릭되었습니다.")

root = tk.Tk()
root.title("Macro Dashboard")
root.geometry("800x500")
root.configure(bg="#F8F9FD") # 배경색: 아주 연한 회색/보라빛

# --- 1. 왼쪽 사이드바 영역 ---
sidebar = tk.Frame(root, width=200, bg="#FFFFFF", relief="flat")
sidebar.pack(side="left", fill="y")

# 사이드바 로고/타입
logo_label = tk.Label(sidebar, text="S Shoppy", font=("Arial", 14, "bold"), 
                      bg="#FFFFFF", fg="#333333", pady=30)
logo_label.pack()

# 사이드바 메뉴 예시 (이미지처럼 아이콘 대신 텍스트로)
menus = ["Overview", "Transactions", "Messages", "My Products", "Account"]
for menu in menus:
    fg_color = "#4B7BFF" if menu == "Overview" else "#A0A0A0" # Overview만 파란색
    tk.Label(sidebar, text=menu, font=("Arial", 10), bg="#FFFFFF", 
             fg=fg_color, pady=10, cursor="hand2").pack(anchor="w", padx=30)

# --- 2. 메인 콘텐츠 영역 ---
main_canvas = tk.Frame(root, bg="#F8F9FD", padx=40, pady=30)
main_canvas.pack(side="right", expand=True, fill="both")

# 헤더 (Overview)
header_label = tk.Label(main_canvas, text="Overview", font=("Arial", 18, "bold"), 
                        bg="#F8F9FD", fg="#2D3436")
header_label.pack(anchor="w")

# --- 3. 카드형 레이아웃 (이미지 중간의 흰색 박스들) ---
card_frame = tk.Frame(main_canvas, bg="#F8F9FD")
card_frame.pack(fill="x", pady=20)

# 가짜 데이터 카드 1
card1 = tk.Frame(card_frame, bg="white", padx=20, pady=20, highlightthickness=1, highlightbackground="#EEEEEE")
card1.pack(side="left", expand=True, fill="both", padx=5)
tk.Label(card1, text="Active Orders", font=("Arial", 9), bg="white", fg="#ADADAD").pack(anchor="w")
tk.Label(card1, text="12,018", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")

# 가짜 데이터 카드 2 (파란색 포인트 버튼 포함)
card2 = tk.Frame(card_frame, bg="white", padx=20, pady=20, highlightthickness=1, highlightbackground="#EEEEEE")
card2.pack(side="left", expand=True, fill="both", padx=5)
tk.Label(card2, text="Personal Balance", font=("Arial", 9), bg="white", fg="#ADADAD").pack(anchor="w")
tk.Label(card2, text="$2390.20", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")

# --- 4. 실제 실행 버튼 (이미지의 파란색 Withdraw 버튼 스타일) ---
run_btn = tk.Button(main_canvas, text="RUN MACRO", command=on_click,
                    bg="#4B7BFF", fg="white", font=("Arial", 11, "bold"),
                    relief="flat", padx=40, pady=15, cursor="hand2")
run_btn.pack(pady=30)

root.mainloop()
