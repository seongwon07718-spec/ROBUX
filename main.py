class VendingSettingModal(discord.ui.Modal, title="자판기 설정"):
    title_input = discord.ui.TextInput(
        label="자판기 제목",
        placeholder="예: 구매하기",
        required=True,
        max_length=100,
    )
    desc_input = discord.ui.TextInput(
        label="자판기 설명",
        style=discord.TextStyle.long,
        placeholder="설명을 입력하세요",
        required=False,
        max_length=500,
    )
    color_input = discord.ui.TextInput(
        label="컨테이너 색상 (HEX 코드)",
        placeholder="예: #FFFFFF 또는 FFFFFF",
        required=True,
        max_length=7,
    )
    feature_select = discord.ui.Select(
        placeholder="활성화할 버튼들을 선택하세요",
        min_values=1,
        max_values=4,
        required=True,   # Modal 전용, discord.py 2.6+
        options=[
            discord.SelectOption(label="제품", value="제품"),
            discord.SelectOption(label="구매", value="구매"),
            discord.SelectOption(label="충전", value="충전"),
            discord.SelectOption(label="정보", value="정보"),
        ]
    )

    async def on_submit(self, interaction: discord.Interaction):
        hex_color = self.color_input.value.strip().replace(" ", "")
        if not hex_color.startswith("#"):
            hex_color = f"#{hex_color}"
        try:
            final_color = discord.Color.from_str(hex_color)
        except:
            hex_color = "#5865F2"
            final_color = discord.Color.from_str(hex_color)

        selected_values = self.feature_select.values
        enabled_str = " ".join(selected_values)

        safe_name = "".join(c for c in interaction.guild.name if c.isalnum() or c in (" ", "_", "-")).strip()
        db_path = os.path.join(DB_DIR, f"{safe_name}.db")

        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE info 
                SET vending_title = ?, vending_description = ?, accent_color = ?, enabled_features = ?
                WHERE guild_id = ?
            """, (self.title_input.value, self.desc_input.value, hex_color, enabled_str, str(interaction.guild.id)))

        await interaction.response.send_message(
            view=SimpleLayout(
                "## 설정 저장 완료",
                f"> **색상:** `{hex_color}`\n> **활성 버튼:** `{enabled_str}`",
                final_color
            ),
            ephemeral=True
        )
