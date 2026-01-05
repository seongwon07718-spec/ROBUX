# --- [수정] 결과 확인 뷰 (GIF 합성 로직) ---
class ResultShowView(discord.ui.View):
    def __init__(self, bet_id, c_data, p_data, result):
        super().__init__(timeout=None)
        self.bet_id = bet_id
        self.c = c_data
        self.p = p_data
        self.result = result

    @discord.ui.button(label="VIEW", style=discord.ButtonStyle.success)
    async def view_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.c['id'], self.p['id']]:
            return await interaction.response.send_message("참여자 전용입니다.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        final_gif_path = await create_merged_gif(self.result, self.c, self.p, self.bet_id)
        
        if final_gif_path and os.path.exists(final_gif_path):
            file = discord.File(final_gif_path, filename="result.gif")
            embed = discord.Embed(color=0xffffff)
            embed.set_image(url="attachment://result.gif")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            os.remove(final_gif_path)
        else:
            await interaction.followup.send("GIF 파일을 찾을 수 없습니다.", ephemeral=True)

# --- [수정] 베팅 참여 뷰 (공개 채널용) ---
class BettingProcessView(discord.ui.View):
    def __init__(self, creator, side, res):
        super().__init__(timeout=None)
        self.creator = creator
        self.side = side
        self.res = res

    @discord.ui.button(label="참가하기 (JOIN)", style=discord.ButtonStyle.primary, emoji="🔥")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.creator.id:
            return await interaction.response.send_message("본인 게임은 참가 불가합니다.", ephemeral=True)
        
        bet_id = str(uuid.uuid4()).replace("-", "").upper()[:12]
        c_rid = get_roblox_id(self.creator.id)
        p_rid = get_roblox_id(interaction.user.id)
        
        if not c_rid or not p_rid:
            return await interaction.response.send_message("양쪽 유저 모두 인증이 필요합니다.", ephemeral=True)

        c_thumb = await get_roblox_thumb(c_rid)
        p_thumb = await get_roblox_thumb(p_rid)
        
        c_data = {'id': self.creator.id, 'name': self.creator.display_name, 'thumb': c_thumb, 'side': self.side}
        p_data = {'id': interaction.user.id, 'name': interaction.user.display_name, 'thumb': p_thumb, 'side': 'T' if self.side == 'H' else 'H'}
        
        # DB 저장 (로블록스 ID 포함)
        save_bet_info(bet_id, self.creator.id, c_rid, interaction.user.id, p_rid, self.res)
        
        # 결과 뷰로 전환
        await interaction.message.edit(view=ResultShowView(bet_id, c_data, p_data, self.res))
        await interaction.response.send_message("참가 완료! VIEW 버튼을 눌러 결과를 확인하세요.", ephemeral=True)

# --- [수정] 코인 선택 뷰 (공개 채널 전송) ---
class CoinChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_choice(self, interaction: discord.Interaction, user_side: str):
        result_side = random.choice(["H", "T"])
        
        wait_embed = discord.Embed(
            title="🎯 BloxFlip - 새로운 베팅!",
            description=f"**╰ 생성자 ㅣ {interaction.user.mention}\n╰ 선택 ㅣ {user_side}**\n\n**아래 버튼을 눌러 참가하세요!**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        wait_embed.set_image(url=img_url)
        
        # 채널에 공개 전송
        await interaction.channel.send(embed=wait_embed, view=BettingProcessView(interaction.user, user_side, result_side))
        await interaction.response.send_message("공개 채널에 베팅이 게시되었습니다!", ephemeral=True)

    @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji(name="emoji_23", id=1457645330240634880))
    async def head_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "H")

    @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="emoji_22", id=1457645454887096425))
    async def tail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "T")

# --- [수정] 인증 확인 부분 (로블록스 ID 자동 저장) ---
class VerifyCheckView(discord.ui.View):
    # ... (생략된 기존 __init__ 유지) ...
    @discord.ui.button(label="프로필 수정 완료", style=discord.ButtonStyle.gray, emoji=discord.PartialEmoji(name="check_box_90", id=1455996410070700225))
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ... (기존 API 체크 로직 유지) ...
        if self.verify_key in description:
            user_id = res_json["data"][0]["id"] # 로블록스 ID 추출
            role = interaction.guild.get_role(VERIFY_ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
                # [수정] 로블록스 ID 자동 저장 호출
                save_verified_user(interaction.user.id, interaction.user.name, self.roblox_name, user_id)
                # ... (이하 생략) ...
