import tkinter as tk

def main():
    root = tk.Tk()
    root.title("Macro White Edition")
    root.geometry("900x650")
    root.configure(bg="#F5F7FA") # 연한 그레이빛 배경

    # --- 상단 타이틀 ---
    header = tk.Frame(root, bg="#F5F7FA", pady=20)
    header.pack(fill="x", padx=40)
    tk.Label(header, text="Dashboard", font=("Apple SD Gothic Neo", 24, "bold"), 
             bg="#F5F7FA", fg="#2D3436").pack(side="left")

    # --- 메인 컨테이너 (그리드 배치) ---
    container = tk.Frame(root, bg="#F5F7FA")
    container.pack(fill="both", expand=True, padx=40, pady=10)

    # 1. 왼쪽 큰 카드 (유저 정보 스타일)
    card_l = tk.Frame(container, bg="white", padx=30, pady=30, highlightthickness=1, highlightbackground="#E1E4E8")
    card_l.place(x=0, y=0, width=500, height=250)
    
    tk.Label(card_l, text="Welcome Back", font=("Arial", 12), bg="white", fg="#636E72").pack(anchor="w")
    tk.Label(card_l, text="David", font=("Arial", 28, "bold"), bg="white", fg="#2D3436").pack(anchor="w", pady=10)
    tk.Label(card_l, text="Balance: $84,250", font=("Arial", 14), bg="white", fg="#0984E3").pack(anchor="w")

    # 2. 오른쪽 카드 (진행률 스타일)
    card_r = tk.Frame(container, bg="white", padx=30, pady=30, highlightthickness=1, highlightbackground="#E1E4E8")
    card_r.place(x=520, y=0, width=300, height=250)
    
    tk.Label(card_r, text="Monthly Progress", font=("Arial", 11, "bold"), bg="white").pack(anchor="w")
    # 가짜 프로그레스 바 (화이트 테마에 맞는 파란색)
    bar_bg = tk.Frame(card_r, bg="#DFE6E9", height=12)
    bar_bg.pack(fill="x", pady=30)
    tk.Frame(bar_bg, bg="#74B9FF", width=180, height=12).pack(side="left")

    # 3. 하단 메뉴 카드 (리스트 스타일)
    card_b = tk.Frame(container, bg="white", padx=20, pady=20, highlightthickness=1, highlightbackground="#E1E4E8")
    card_b.place(x=0, y=270, width=350, height=250)
    
    for item in ["🏠 Home", "❤️ Likes", "📝 My List", "⚙️ Settings"]:
        btn = tk.Label(card_b, text=item, font=("Arial", 11), bg="white", fg="#2D3436", pady=12)
        btn.pack(anchor="w", padx=10)

    # --- 하단 메인 실행 버튼 ---
    # 화이트 테마에 어울리는 세련된 블랙 버튼으로 포인트
    run_btn = tk.Button(root, text="START MACRO SERVICE", 
                        bg="#2D3436", fg="white", font=("Arial", 12, "bold"),
                        relief="flat", width=30, height=2, cursor="hand2",
                        activebackground="#636E72", activeforeground="white")
    run_btn.pack(pady=40)

    root.mainloop()

if __name__ == "__main__":
    main()
