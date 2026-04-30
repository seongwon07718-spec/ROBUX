# ==================== 자판기 설정 Modal ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        # 1. 텍스트 입력항목
        self.title_input = discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
            max_length=100,
        )
        self.desc_input = discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="설명을 입력하세요",
            required=False,
            max_length=500,
        )
        self.color_input = discord.ui.TextInput(
            label="컨테이너 색상 (HEX)",
            placeholder="예: #FFFFFF 또는 FFFFFF",
            required=True,
            max_length=30,
        )

        # 2. 이미지(image_5.png) 방식의 Checkbox 설정
        # 해외에서 사용하는 최신 V2 인터페이스 방식입니다.
        self.rb = discord.ui.Label(
            text="버튼 표시 선택",
            component=discord.ui.Checkbox( # CheckboxGroup 대신 Checkbox 사용
                options=[
                    discord.ui.CheckboxGroupOption(label="제품", value="제품"),
                    discord.ui.CheckboxGroupOption(label="구매", value="구매"),
                    discord.ui.CheckboxGroupOption(label="충전", value="충전"),
                    discord.ui.CheckboxGroupOption(label="정보", value="정보"),
                ],
                min_values=1,
                max_values=4
            )
        )

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.rb)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 텍스트 값 가져오기
            title = self.title_input.value.strip() or "구매하기"
            description = self.desc_input.value.strip() if self.desc_input.value else "아래 버튼을 눌러 이용해주세요"
            
            # 색상 처리 (# 기호 자동 보정)
            raw_color = self.color_input.value.strip().replace(" ", "")
            color_str = raw_color if raw_color.startswith("#") else f"#{raw_color}"
            
            try:
                final_color = discord.Color.from_str(color_str)
            except:
                color_str = "#5865F2"
                final_color = discord.Color.from_str(color_str)

            # 3. 이미지 방식의 데이터 추출 (해외 표준 방식)
            # 이미지 5번 하단의 interaction.data 구조를 사용하여 선택된 값을 가져옵니다.
            try:
                # 일반적인 self.rb.component.values가 작동하지 않을 경우를 대비한 직접 추출 방식
                selected_values = interaction.data['components'][-1]['components'][0]['value']
                # 만약 위 방식이 에러난다면: selected_values = self.rb.component.values
            except:
                selected_values = self.rb.component.values
            
            enabled_str = " ".join(selected_values) if selected_values else "제품 구매 충전 정보"

            # DB 저장 로직
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
                    title="✅ 설정 완료", 
                    description=f"색상: `{color_str}`\n활성 버튼: `{enabled_str}`",
                    color=final_color
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"에러 발생: {e}")
            await interaction.response.send_message(f"오류가 발생했습니다: {e}", ephemeral=True)
