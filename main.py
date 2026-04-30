class RegisterConfirmLayout(discord.ui.LayoutView):
    """서버 등록 확인 - ActionRow + 동적 callback 방식"""
    def __init__(self, key: str, days: int, expires: str, guild_name: str):
        super().__init__(timeout=None)
        self.license_key = key
        self.days = days
        self.expires = expires
        self.guild_name = guild_name

        # Container 생성
        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 서버 등록 확인"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(
                content=(
                    f"> **라이센스:** `{key}`\n"
                    f"> **서버:** {guild_name}\n"
                    f"> **기간:** {days}일\n"
                    f"> **만료일:** {expires}\n\n"
                    "**이 서버에 등록하시겠습니까?**"
                )
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            accent_color=discord.Color.from_str("#5865F2"),
        )

        # 진행 버튼 + callback 동적 연결
        btn_confirm = discord.ui.Button(
            label="진행", 
            style=discord.ButtonStyle.primary
        )
        btn_confirm.callback = self.confirm_callback   # ← 동적 연결

        # 취소 버튼 + callback 동적 연결
        btn_cancel = discord.ui.Button(
            label="취소", 
            style=discord.ButtonStyle.secondary
        )
        btn_cancel.callback = self.cancel_callback     # ← 동적 연결

        # ActionRow에 버튼 추가 후 Container에 넣기
        action_row = discord.ui.ActionRow(btn_confirm, btn_cancel)
        container.add_item(action_row)

        self.add_item(container)

    # ==================== 진행 버튼 콜백 ====================
    async def confirm_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = sqlite3.connect(LICENSE_DB)
            c = conn.cursor()
            c.execute("SELECT used FROM licenses WHERE key = ?", (self.license_key,))
            row = c.fetchone()

            if not row or row[0] == 1:
                conn.close()
                await interaction.edit_original_response(
                    view=SimpleLayout("## 등록 실패", "이미 사용된 라이센스이거나 유효하지 않습니다.", discord.Color.red())
                )
                return

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            guild = interaction.guild

            c.execute(
                "UPDATE licenses SET used = 1, guild_id = ?, guild_name = ?, expires_at = ? WHERE key = ?",
                (str(guild.id), guild.name, self.expires, self.license_key)
            )
            conn.commit()
            conn.close()

            # 서버 DB 등록
            db_path = init_guild_db(str(guild.id), guild.name)
            with sqlite3.connect(db_path) as guild_conn:
                gc = guild_conn.cursor()
                gc.execute(
                    "INSERT OR REPLACE INTO info VALUES (?, ?, ?, ?, ?)",
                    (str(guild.id), guild.name, self.license_key, now, self.expires)
                )

            await interaction.edit_original_response(
                view=SimpleLayout(
                    "## 등록 완료",
                    f"> **서버:** {guild.name}\n> **기간:** {self.days}일\n> **만료일:** {self.expires}\n\n자판기 봇이 정상적으로 등록되었습니다.",
                    discord.Color.green()
                )
            )

        except Exception as e:
            print(f"[등록 진행 오류] {e}")
            await interaction.edit_original_response(
                view=SimpleLayout("## 오류 발생", "처리 중 문제가 발생했습니다.", discord.Color.red())
            )

    # ==================== 취소 버튼 콜백 ====================
    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        await interaction.edit_original_response(
            view=SimpleLayout(
                "## 등록 취소",
                "등록이 취소되었습니다.\n다시 등록하려면 `/등록` 명령어를 사용하세요.",
                discord.Color.from_str("#99AAB5")
            )
        )
