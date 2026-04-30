# ==================== 자판기 설정 Modal (최신 V2 방식) ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        # 1. 일반 텍스트 입력항목 (제목, 설명)
        self.title_input = discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
        )
        self.desc_input = discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="하단 설명을 입력하세요",
            required=False,
        )

        # 2. 색상 코드 입력 (#ffffff 또는 ffffff 처리)
        self.color_input = discord.ui.TextInput(
            label="컨테이너 색상 (HEX 코드)",
            placeholder="예: #FFFFFF 또는 FFFFFF",
            required=True,
            max_length=7,
        )

        # 3. 이미지(image_5.png) 기반 체크박스 구현
        # discord.ui.Checkbox를 사용하여 다중 선택 가능하게 구성
        self.features_check = discord.ui.Label(
            text="활성화할 버튼을 선택하세요",
            component=discord.ui.Checkbox(
                options=[
                    discord.ui.Option(label="제품", value="제품"),
                    discord.ui.Option(label="구매", value="구매"),
                    discord.ui.Option(label="충전", value="충전"),
                    discord.ui.Option(label="정보", value="정보"),
                ],
                min_values=1,
                max_values=4,
                custom_id="vending_features"
            )
        )

        # 아이템 순서대로 추가
        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.features_check)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 색상 코드 전처리 (# 기호 보정)
            hex_color = self.color_input.value.strip().replace(" ", "")
            if not hex_color.startswith("#"):
                hex_color = f"#{hex_color}"
            
            # 색상 코드 검증
            try:
                final_color = discord.Color.from_str(hex_color)
            except ValueError:
                hex_color = "#5865F2" # 오류 시 기본 파란색
                final_color = discord.Color.from_str(hex_color)

            # 4. 이미지 5번의 데이터 추출 방식 적용
            # 최신 API에서는 component.values를 통해 바로 접근 가능합니다.
            selected_options = self.features_check.component.values
            enabled_features = " ".join(selected_options) if selected_options else "제품 구매 충전 정보"

            # DB 업데이트
            safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
            db_path = os.path.join(DB_DIR, f"{safe_name}.db")

            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE info 
                    SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                    WHERE guild_id = ?
                """, (self.title_input.value, self.desc_input.value, hex_color, enabled_features, str(interaction.guild.id)))
                conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ 자판기 설정이 저장되었습니다.", 
                    description=f"**색상:** `{hex_color}`\n**활성 버튼:** `{enabled_features}`",
                    color=final_color
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"[설정 오류] {e}")
            await interaction.response.send_message("설정 저장 중 오류가 발생했습니다. 라이브러리 버전을 확인해주세요.", ephemeral=True)
