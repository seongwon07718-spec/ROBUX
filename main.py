# ==================== 자판기 설정 Modal ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        # 1. 텍스트 입력 아이템들
        self.title_input = discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
            max_length=100,
        )
        self.desc_input = discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="자판기 하단에 표시될 설명을 입력하세요 (선택 사항)",
            required=False,
            max_length=500,
        )
        self.color_input = discord.ui.TextInput(
            label="컨테이너 색상 (HEX 코드)",
            placeholder="예: #FFFFFF 또는 FFFFFF",
            required=True,
            max_length=30,
        )

        # 2. 이미지의 방식 그대로 적용 (Label 안에 CheckboxGroup 구성)
        self.rb = discord.ui.Label(
            text="버튼 표시 선택",
            component=discord.ui.CheckboxGroup(
                options=[
                    discord.ui.CheckboxGroupOption(label="제품", value="제품"),
                    discord.ui.CheckboxGroupOption(label="구매", value="구매"),
                    discord.ui.CheckboxGroupOption(label="충전", value="충전"),
                    discord.ui.CheckboxGroupOption(label="정보", value="정보"),
                ]
            )
        )

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.rb)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            title = self.title_input.value.strip() or "구매하기"
            description = self.desc_input.value.strip() if self.desc_input.value else "아래 버튼을 눌러 이용해주세요"
            
            # --- 색상 코드 처리 로직 ---
            raw_color = self.color_input.value.strip().replace(" ", "")
            
            if raw_color.startswith("#"):
                # #FFFFFF 형식일 때
                color_str = raw_color.upper()
            else:
                # FFFFFF 형식일 때 #을 붙여줌
                color_str = f"#{raw_color.upper()}"
            
            # 유효한 HEX 코드인지 검증 (실패 시 기본 색상 적용)
            try:
                final_color = discord.Color.from_str(color_str)
            except ValueError:
                color_str = "#5865F2" # 잘못된 코드 입력 시 디스코드 블루 적용
                final_color = discord.Color.from_str(color_str)

            # 체크박스 값 추출
            selected_values = self.rb.component.values
            enabled_str = " ".join(selected_values) if selected_values else "제품 구매 충전 정보"

            # DB 저장
            safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
            db_path = os.path.join(DB_DIR, f"{safe_name}.db")

            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE info 
                    SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                    WHERE guild_id = ?
                """, (title, description, color_str, enabled_str, str(interaction.guild.id)))
                conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="설정이 저장되었습니다", 
                    description=f"적용된 색상 코드: `{color_str}`",
                    color=final_color
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"[Modal 오류] {e}")
            await interaction.response.send_message("설정 저장 중 오류가 발생했습니다.", ephemeral=True)
