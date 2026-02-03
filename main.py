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

        # --- 메인 레이아웃 ---
        self.create_user_card(30, 30)
        self.create_menu_card(30, 270)
        self.create_progress_card(370, 30)
        self.create_download_button(370, 410)
        self.create_graph_section(710, 30)

    def create_user_card(self, x, y):
        # 모든 위젯 생성 시 width, height를 명시적으로 전달
        card = ctk.CTkFrame(self, width=320, height=220, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        
        ctk.CTkLabel(card, width=100, height=30, text="● OrbStak", font=("Arial", 18, "bold"), text_color="#2D3436").place(x=25, y=25)
        ctk.CTkLabel(card, width=100, height=20, text="Welcome back!", font=("Arial", 11), text_color="#A0A0A0").place(x=190, y=55)
        
        avatar = ctk.CTkFrame(card, width=70, height=70, corner_radius=15, fg_color="#F2F4F7")
        avatar.place(x=40, y=75)
        
        ctk.CTkLabel(card, width=50, height=25, text="David", font=("Arial", 16, "bold")).place(x=48, y=155)
        ctk.CTkLabel(card, width=100, height=30, text="$84,250", font=("Arial", 26, "bold"), text_color="#2D3436").place(x=180, y=150)

    def create_menu_card(self, x, y):
        card = ctk.CTkFrame(self, width=320, height=350, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        
        # 버튼 생성 시 width, height 필수
        home_btn = ctk.CTkButton(card, width=270, height=50, text="🏠 Home", corner_radius=15, fg_color="#2D3436", text_color="white", hover_color="#454545")
        home_btn.place(x=25, y=30)
        
        ctk.CTkLabel(card, width=100, height=30, text="❤️ Likes", font=("Arial", 13), text_color="#A0A0A0").place(x=50, y=110)
        ctk.CTkLabel(card, width=100, height=30, text="📋 My List", font=("Arial", 13), text_color="#A0A0A0").place(x=50, y=180)

    def create_progress_card(self, x, y):
        card = ctk.CTkFrame(self, width=320, height=350, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        card.place(x=x, y=y)
        
        ctk.CTkLabel(card, width=150, height=30, text="Monthly Progress", font=("Arial", 13, "bold")).place(x=25, y=25)
        
        bar = ctk.CTkProgressBar(card, width=270, height=12, corner_radius=10, fg_color="#F2F4F7", progress_color="#2D3436")
        bar.place(x=25, y=75)
        bar.set(0.7)
        
        # 도넛 차트 (이미지 중앙의 1.2k 차트)
        fig, ax = plt.subplots(figsize=(2, 2), dpi=100)
        ax.pie([70, 30], colors=['#2D3436', '#F2F4F7'], startangle=90, wedgeprops={'width': 0.3})
        ax.text(0, 0, '1.2k', ha='center', va='center', fontsize=12, fontweight='bold')
        fig.patch.set_facecolor('white')
        ax.axis('equal')
        
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().place(x=60, y=120)
        plt.close(fig)

    def create_download_button(self, x, y):
        btn = ctk.CTkButton(self, width=320, height=65, text="DOWNLOAD REPORT", corner_radius=20, 
                             fg_color="#2D3436", text_color="white", font=("Arial", 14, "bold"), hover_color="#454545")
        btn.place(x=x, y=y)

    def create_graph_section(self, x, y):
        # 상단 곡선 그래프
        g1 = ctk.CTkFrame(self, width=350, height=220, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        g1.place(x=x, y=y)
        
        fig1, ax1 = plt.subplots(figsize=(3.2, 1.8), dpi=100)
        x_data = np.linspace(0, 10, 100)
        y_data = np.exp(x_data/10) # 부드러운 상승 곡선
        ax1.plot(x_data, y_data, color='#2D3436', lw=2.5)
        ax1.axis('off')
        fig1.patch.set_facecolor('white')
        
        canvas1 = FigureCanvasTkAgg(fig1, master=g1)
        canvas1.get_tk_widget().place(x=15, y=40)
        plt.close(fig1)

        # 하단 막대 그래프
        g2 = ctk.CTkFrame(self, width=350, height=220, corner_radius=25, fg_color="white", border_width=1, border_color="#E1E4E8")
        g2.place(x=x, y=250)
        
        fig2, ax2 = plt.subplots(figsize=(3.2, 1.8), dpi=100)
        ax2.bar(['J', 'F', 'M', 'A', 'M'], [4, 7, 5, 8, 9], color='#2D3436', width=0.4)
        ax2.axis('off')
        fig2.patch.set_facecolor('white')
        
        canvas2 = FigureCanvasTkAgg(fig2, master=g2)
        canvas2.get_tk_widget().place(x=15, y=30)
        plt.close(fig2)

if __name__ == "__main__":
    app = OrbStakUI()
    app.mainloop()
