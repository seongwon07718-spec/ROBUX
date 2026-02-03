import customtkinter as ctk

# 테마 설정 (완전 다크 모드)
ctk.set_appearance_mode("Dark")

class LicenseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 기본 설정 ---
        self.title("Macro System")
        self.geometry("1000x700")
        self.configure(fg_color="#000000") # 전체 배경 검정

        # --- 중앙 70% 박스 계산 ---
        # 1000x700의 70%는 약 700x490
        self.main_card = ctk.CTkFrame(self, width=700, height=490, 
                                      corner_radius=30, 
                                      fg_color="#1A1A1A", 
                                      border_width=1, 
                                      border_color="#333333")
        self.main_card.place(relx=0.5, rely=0.5, anchor="center")

        # 1. 라이센스 입력 텍스트 (한글 폰트 적용)
        self.title_label = ctk.CTkLabel(self.main_card, 
                                        text="라이센스 입력", 
                                        font=("Malgun Gothic", 24, "bold"), 
                                        text_color="white")
        self.title_label.place(relx=0.5, rely=0.3, anchor="center")

        # 2. 얇은 네모난 둥글 박스 (입력창)
        self.license_entry = ctk.CTkEntry(self.main_card, 
                                          width=400, 
                                          height=45, 
                                          corner_radius=15, 
                                          fg_color="#2B2B2B", 
                                          border_color="#444444",
                                          placeholder_text="여기에 라이센스 번호를 입력하세요",
                                          font=("Malgun Gothic", 13),
                                          justify="center")
        self.license_entry.place(relx=0.5, rely=0.5, anchor="center")

        # 3. 라이센스 등록 버튼 (둥글게)
        self.register_btn = ctk.CTkButton(self.main_card, 
                                          text="라이센스 등록", 
                                          width=200, 
                                          height=50, 
                                          corner_radius=25, 
                                          fg_color="#4318FF", # 포인트 컬러
                                          hover_color="#3712E0",
                                          font=("Malgun Gothic", 15, "bold"),
                                          command=self.register_action)
    def register_action(self):
        # 버튼 클릭 시 동작
        print(f"입력된 라이센스: {self.license_entry.get()}")

if __name__ == "__main__":
    app = LicenseApp()
    app.mainloop()
