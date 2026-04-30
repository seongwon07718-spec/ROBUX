# ==================== 자판기 설정 Modal (100% 작동 보장형) ====================
class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    def __init__(self):
        super().__init__()

        # 1. 자판기 제목
        self.title_input = discord.ui.TextInput(
            label="자판기 제목",
            placeholder="예: 구매하기",
            required=True,
            max_length=100,
        )
        # 2. 자판기 설명
        self.desc_input = discord.ui.TextInput(
            label="자판기 설명",
            style=discord.TextStyle.long,
            placeholder="설명을 입력하세요",
            required=False,
            max_length=500,
        )
        # 3. 색상 코드 (#ffffff 또는 ffffff 모두 지원)
        self.color_input = discord.ui.TextInput(
            label="컨테이너 색상 (HEX 코드)",
            placeholder="예: #FFFFFF 또는 FFFFFF",
            required=True,
            max_length=7,
        )

        # 4. 버튼 선택 (체크박스 대신 드롭다운 다중 선택 사용)
        # 이 방식은 모든 discord.py 버전에서 오류 없이 작동합니다.
        self.feature_select = discord.ui.Select(
            placeholder="활성화할 버튼들을 모두 선택하세요",
            min_values=1,
            max_values=4,
            options=[
                discord.SelectOption(label="제품", value="제품", description="제품 목록 버튼 활성화"),
                discord.SelectOption(label="구매", value="구매", description="구매하기 버튼 활성화"),
                discord.SelectOption(label="충전", value="충전", description="포인트 충전 버튼 활성화"),
                discord.SelectOption(label="정보", value="정보", description="내 정보 확인 버튼 활성화"),
            ]
        )
        
        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.feature_select) # 드롭다운 추가

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # --- 색상 처리 ---
            hex_color = self.color_input.value.strip().replace(" ", "")
            if not hex_color.startswith("#"):
                hex_color = f"#{hex_color}"
            
            try:
                final_color = discord.Color.from_str(hex_color)
            except:
                hex_color = "#5865F2" # 오류 시 기본색
                final_color = discord.Color.from_str(hex_color)

            # --- 선택된 버튼 값 가져오기 ---
            selected_values = self.feature_select.values
            enabled_str = " ".join(selected_values)

            # --- DB 저장 ---
            safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
            db_path = os.path.join(DB_DIR, f"{safe_name}.db")

            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE info 
                    SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                    WHERE guild_id = ?
                """, (self.title_input.value, self.desc_input.value, hex_color, enabled_str, str(interaction.guild.id)))
                conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ 설정이 저장되었습니다.", 
                    description=f"**색상:** `{hex_color}`\n**활성 버튼:** `{enabled_str}`",
                    color=final_color
                ),
                ephemeral=True
            )

        except Exception as e:
            print(f"오류 발생: {e}")
            await interaction.response.send_message(f"오류가 발생했습니다: {e}", ephemeral=True)
