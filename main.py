class VerifyInfoView(discord.ui.View):
    def __init__(self, data, per_page=10):
        super().__init__(timeout=60)
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(data) - 1) // per_page + 1 if data else 1

    def make_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_data = self.data[start:end]

        embed = discord.Embed(
            title="🛡️ 인증된 유저 목록",
            description=f"총 인증 인원: **{len(self.data)}명**",
            color=discord.Color.blue()
        )

        if not page_data:
            embed.add_field(name="정보", value="인증된 유저가 없습니다.")
        else:
            list_text = ""
            for i, user in enumerate(page_data, start=start + 1):
                list_text += f"{i}. {user['discord_name']} | {user['roblox_name']}\n"
            embed.add_field(name=f"목록 (페이지 {self.current_page + 1}/{self.total_pages})", value=list_text)
        
        return embed

    @discord.ui.button(label="<", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.send_message("첫 페이지입니다.", ephemeral=True)

    @discord.ui.button(label=">", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.send_message("마지막 페이지입니다.", ephemeral=True)

# 명령어 등록
@bot.tree.command(name="verify_info", description="인증된 유저 목록을 확인합니다.")
async def verify_info(interaction: discord.Interaction):
    db_data = load_db()
    view = VerifyInfoView(db_data)
    await interaction.response.send_message(embed=view.make_embed(), view=view)

