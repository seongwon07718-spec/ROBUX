import tkinter as tk

def main():
    root = tk.Tk()
    root.title("OrbStak Dashboard")
    root.geometry("1000x700")
    root.configure(bg="#F2F4F7") # 배경: 연한 그레이

    # --- 전체 배치용 컨테이너 ---
    main_frame = tk.Frame(root, bg="#F2F4F7")
    main_frame.pack(expand=True, fill="both", padx=20, pady=20)

    # 1. 왼쪽 위: 프로필 카드
    card_user = tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8")
    card_user.place(x=0, y=0, width=320, height=220)
    
    tk.Label(card_user, text="● OrbStak", font=("Arial", 14, "bold"), bg="white", fg="#2D3436").place(x=20, y=20)
    tk.Label(card_user, text="Welcome back", font=("Arial", 10), bg="white", fg="#A0A0A0").place(x=180, y=50)
    
    # David 프로필 영역
    tk.Frame(card_user, bg="#F2F4F7", width=60, height=60).place(x=40, y=70) # 아바타 박스
    tk.Label(card_user, text="David", font=("Arial", 14, "bold"), bg="white").place(x=45, y=140)
    tk.Label(card_user, text="Balance", font=("Arial", 9), bg="white", fg="#A0A0A0").place(x=230, y=120)
    tk.Label(card_user, text="$84,250", font=("Arial", 20, "bold"), bg="white", fg="#2D3436").place(x=170, y=140)

    # 2. 왼쪽 아래: 메뉴 리스트
    card_menu = tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8")
    card_menu.place(x=0, y=240, width=320, height=350)
    
    # Home (강조된 스타일)
    home_bar = tk.Frame(card_menu, bg="#F2F4F7")
    home_bar.place(x=20, y=30, width=280, height=50)
    tk.Label(home_bar, text="🏠 Home", font=("Arial", 11, "bold"), bg="#F2F4F7", fg="#2D3436").pack(side="left", padx=15)

    tk.Label(card_menu, text="❤️ Likes", font=("Arial", 11), bg="white", fg="#A0A0A0").place(x=40, y=110)
    tk.Label(card_menu, text="📋 My List", font=("Arial", 11), bg="white", fg="#A0A0A0").place(x=40, y=180)

    # 3. 중앙: Monthly Progress 박스
    card_prog = tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8")
    card_prog.place(x=340, y=0, width=320, height=350)
    
    tk.Label(card_prog, text="Monthly Progress", font=("Arial", 10, "bold"), bg="white").place(x=20, y=20)
    tk.Label(card_prog, text="8 out of 10", font=("Arial", 9), bg="white", fg="#A0A0A0").place(x=230, y=45)
    
    # 프로그레스 바
    tk.Frame(card_prog, bg="#F2F4F7", width=280, height=10).place(x=20, y=70)
    tk.Frame(card_prog, bg="#2D3436", width=180, height=10).place(x=20, y=70)

    # 중앙 원형 차트 느낌 박스
    tk.Frame(card_prog, bg="#F2F4F7", width=120, height=120).place(x=40, y=130)
    tk.Label(card_prog, text="1.2k", font=("Arial", 16, "bold"), bg="#F2F4F7").place(x=75, y=175)

    # 4. 중앙 아래: 버튼 3개 (Sign in, Login, Download)
    tk.Button(main_frame, text="Sign in", bg="white", relief="flat", highlightthickness=1).place(x=340, y=370, width=150, height=50)
    tk.Button(main_frame, text="Login", bg="white", relief="flat", highlightthickness=1).place(x=510, y=370, width=150, height=50)
    
    download_btn = tk.Button(main_frame, text="DOWNLOAD REPORT", bg="#2D3436", fg="white", 
                             font=("Arial", 10, "bold"), relief="flat")
    download_btn.place(x=340, y=440, width=320, height=60)

    # 5. 오른쪽: 그래프 박스들 (이미지의 3단 구성)
    # 상단 그래프
    tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8").place(x=680, y=0, width=280, height=220)
    # 중간 그래프
    tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8").place(x=680, y=240, width=280, height=160)
    # 하단 그래프
    tk.Frame(main_frame, bg="white", highlightthickness=1, highlightbackground="#E1E4E8").place(x=680, y=420, width=280, height=120)

    root.mainloop()

if __name__ == "__main__":
    main()
