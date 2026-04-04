# --- 로벅스 계산기 모달 (수량 입력 -> 금액 출력 방식) ---
class RobuxCalculatorModal(ui.Modal, title="로벅스 가격 계산기"):
    robux_amount = ui.TextInput(
        label="구매하실 로벅스 수량 (R$)", 
        placeholder="예: 1300", 
        min_length=1
    )

    async def on_submit(self, it: discord.Interaction):
        try:
            # 사용자가 입력한 로벅스 수량
            target_robux = int(self.robux_amount.value)
            
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            row = cur.fetchone()
            conn.close()

            # 설정된 비율 (1.0당 로벅스 수량, 기본값 1300)
            rate = int(row[0]) if row else 1300

            # 계산 로직: (원하는 로벅스 / 비율) * 10000 = 필요한 금액
            # 예: 1.0당 1300인데 2600을 사고 싶다면 (2600 / 1300) * 10000 = 20,000원
            required_money = int((target_robux / rate) * 10000)
            
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay("### 🧮 계산 결과"))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(
                f"- **희망 로벅스**: `{target_robux:,} R$`\n"
                f"- **현재 비율**: `1.0 = {rate} R$`\n\n"
                f"### 💳 필요한 충전 금액: `{required_money:,}원`"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay("-# 계산된 금액만큼 충전 후 구매를 진행해주세요."))
            
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
            
        except ValueError:
            await it.response.send_message("숫자만 정확히 입력해주세요.", ephemeral=True)
        except Exception as e:
            await it.response.send_message(f"계산 중 오류가 발생했습니다: {e}", ephemeral=True)

# --- 자판기 클래스 내 콜백 연결 (기존 구조 유지) ---
class RobuxVending(ui.LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # ... (기존 build_main_menu 생략) ...

    async def calc_callback(self, it: discord.Interaction):
        """계산기 버튼 클릭 시 수량 입력 모달을 띄움"""
        await it.response.send_modal(RobuxCalculatorModal())

    # ... (기존 콜백들 유지) ...

