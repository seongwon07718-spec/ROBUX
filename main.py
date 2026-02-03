import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np

ctk.set_appearance_mode("Light")

class OrbStakUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OrbStak Dashboard")
        self.geometry("1100x750")
        self.configure(fg_color="#F2F4F7")

        # --- 레이아웃 배치 ---
        # 1. 유저 카드 (David)
        self.create_user_card(30, 30)
        # 2. 메뉴 카드
        self.create_menu_card(30, 270)
        # 3. 중앙 Monthly Progress (도넛 차트 포함)
        self.create_progress_card(370, 30)
        # 4. 하단 실행 버튼
        self.create_download_button(370, 410)
        # 5. 오른쪽 그래프 섹션 (곡선, 막대)
        self.create_graph_section(710, 30)

    def create_user_card(self, x, y):
        card = ctk.CTkFrame(self, width=320, height=220, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        ctk.CTkLabel(card, text="● OrbStak", font=("Arial", 18, "bold"), text_color="#2D3436").place(x=25, y=25)
        ctk.CTkLabel(card, text="Welcome back!", font=("Arial", 11), text_color="#A0A0A0").place(x=190, y=55)
        ctk.CTkFrame(card, width=70, height=70, corner_radius=15, fg_color="#F2F4F7").place(x=40, y=75) # 아바타
        ctk.CTkLabel(card, text="David", font=("Arial", 16, "bold")).place(x=48, y=155)
        ctk.CTkLabel(card, text="Balance", font=("Arial", 10), text_color="#A0A0A0").place(x=230, y=125)
        ctk.CTkLabel(card, text="$84,250", font=("Arial", 26, "bold"), text_color="#2D3436").place(x=180, y=150)

    def create_menu_card(self, x, y):
        card = ctk.CTkFrame(self, width=320, height=350, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        btn = ctk.CTkButton(card, text="🏠 Home", corner_radius=15, fg_color="#2D3436", text_color="white", hover_color="#454545", height=50)
        btn.place(x=25, y=30, width=270)
        ctk.CTkLabel(card, text="❤️ Likes", font=("Arial", 13), text_color="#A0A0A0").place(x=50, y=110)
        ctk.CTkLabel(card, text="📋 My List", font=("Arial", 13), text_color="#A0A0A0").place(x=50, y=180)

    def create_progress_card(self, x, y):
        card = ctk.CTkFrame(self, width=320, height=350, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        ctk.CTkLabel(card, text="Monthly Progress", font=("Arial", 13, "bold")).place(x=25, y=25)
        bar = ctk.CTkProgressBar(card, width=270, height=12, corner_radius=10, fg_color="#F2F4F7", progress_color="#2D3436")
        bar.place(x=25, y=75); bar.set(0.7)
        
        # 도넛 차트 (Matplotlib)
        fig, ax = plt.subplots(figsize=(2, 2), dpi=100)
        ax.pie([70, 30], colors=['#2D3436', '#F2F4F7'], startangle=90, wedgeprops={'width': 0.3})
        ax.text(0, 0, '1.2k', ha='center', va='center', fontsize=12, fontweight='bold')
        fig.patch.set_facecolor('white')
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().place(x=60, y=120)
        plt.close(fig)

    def create_download_button(self, x, y):
        btn = ctk.CTkButton(self, text="DOWNLOAD REPORT", corner_radius=20, fg_color="#2D3436", 
                             text_color="white", font=("Arial", 14, "bold"), height=65, hover_color="#454545")
        btn.place(x=x, y=y, width=320)

    def create_graph_section(self, x, y):
        # 1. 곡선 그래프
        g1 = ctk.CTkFrame(self, width=350, height=220, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        g1.place(x=x, y=y)
        fig1, ax1 = plt.subplots(figsize=(3, 1.5), dpi=100)
        x_data = np.linspace(0, 10, 100); y_data = np.sin(x_data) * 0.5 + 0.5
        ax1.plot(x_data, y_data, color='#2D3436', lw=2)
        ax1.axis('off'); fig1.patch.set_facecolor('white')
        canvas1 = FigureCanvasTkAgg(fig1, master=g1)
        canvas1.get_tk_widget().place(x=10, y=40)
        plt.close(fig1)

        # 2. 막대 그래프
        g2 = ctk.CTkFrame(self, width=350, height=200, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        g2.place(x=x, y=250)
        fig2, ax2 = plt.subplots(figsize=(3, 1.5), dpi=100)
        ax2.bar(['J', 'F', 'M', 'A'], [5, 8, 6, 9], color='#2D3436', width=0.5)
        ax2.axis('off'); fig2.patch.set_facecolor('white')
        canvas2 = FigureCanvasTkAgg(fig2, master=g2)
        canvas2.get_tk_widget().place(x=10, y=30)
        plt.close(fig2)

if __name__ == "__main__":
    app = OrbStakUI()
    app.mainloop()
