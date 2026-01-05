# 1. 결과 확인 뷰 (실시간 합성 로직 포함)
class ResultShowView(discord.ui.View):
    def __init__(self, bet_id, c_data, p_data, result): # 4개의 인자를 정확히 받음
        super().__init__(timeout=None)
        self.bet_id = bet_id
        self.c = c_data
        self.p = p_data
        self.result = result

    @discord.ui.button(label="VIEW", style=discord.ButtonStyle.success)
    async def view_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 참여자 본인 확인
        if interaction.user.id not in [self.c['id'], self.p['id']]:
            return await interaction.response.send_message("참여자 전용입니다.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        # 이미 있는 GIF에 프사와 이름을 합성
        final_gif_path = await create_merged_gif(self.result, self.c, self.p, self.bet_id)
        
        if not final_gif_path or not os.path.exists(final_gif_path):
            return await interaction.followup.send("GIF 생성 중 오류가 발생했습니다. (파일 확인 필요)", ephemeral=True)

        file = discord.File(final_gif_path, filename="result.gif")
        embed = discord.Embed(color=0xffffff)
        embed.set_image(url="attachment://result.gif") # 합성된 이미지만 깔끔하게 노출
        
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        
        # 전송 후 임시 파일 삭제
        if os.path.exists(final_gif_path):
            os.remove(final_gif_path)

# 2. 베팅 대기 뷰 (JOIN 클릭 시 데이터 수집)
class BettingProcessView(discord.ui.View):
    def __init__(self, creator, side, res):
        super().__init__(timeout=None)
        self.creator = creator
        self.side = side
        self.res = res

    @discord.ui.button(label="JOIN", style=discord.ButtonStyle.primary)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.creator.id:
            return await interaction.response.send_message("본인 게임은 참가할 수 없습니다.", ephemeral=True)
        
        # 고유 ID 및 유저 로블록스 데이터 로드
        bet_id = str(uuid.uuid4()).replace("-", "").upper()[:12]
        c_rid = get_roblox_id(self.creator.id)
        p_rid = get_roblox_id(interaction.user.id)
        
        c_thumb = await get_roblox_thumb(c_rid)
        p_thumb = await get_roblox_thumb(p_rid)
        
        # 합성용 데이터 딕셔너리 구성
        c_data = {'id': self.creator.id, 'name': self.creator.display_name, 'thumb': c_thumb, 'side': self.side}
        p_data = {'id': interaction.user.id, 'name': interaction.user.display_name, 'thumb': p_thumb, 'side': 'T' if self.side == 'H' else 'H'}
        
        # DB 저장
        save_bet_info(bet_id, self.creator.id, interaction.user.id, self.res)
        
        # ResultShowView 호출 시 4개의 인자를 모두 전달
        result_view = ResultShowView(bet_id, c_data, p_data, self.res)
        await interaction.message.edit(view=result_view)
        await interaction.response.send_message("참가 완료! VIEW 버튼을 눌러주세요.", ephemeral=True)

# 3. 코인 선택 뷰 (최초 베팅 생성)
class CoinChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_choice(self, interaction: discord.Interaction, user_side: str):
        # 결과 미리 결정
        result_side = random.choice(["H", "T"])
        
        wait_embed = discord.Embed(
            title="BloxFlip - 베팅완료",
            description=f"**╰ {interaction.user.mention}님이 **{user_side}**에 베팅하셨습니다**\n**╰ 상대방이 JOIN 버튼을 누를 때까지 기다려주세요**",
            color=0xffffff
        )
        img_url = "https://cdn.discordapp.com/attachments/1455759161039261791/1457613650276782154/IMG_0845.png"
        wait_embed.set_image(url=img_url)
        
        # [수정] 바로 결과를 보여주는 게 아니라, 다른 사람이 참가할 수 있도록 BettingProcessView를 띄움
        view = BettingProcessView(interaction.user, user_side, result_side)
        await interaction.response.edit_message(embed=wait_embed, view=view)

    @discord.ui.button(label="앞면 (H)", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji(name="emoji_23", id=1457645330240634880))
    async def head_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "H")

    @discord.ui.button(label="뒷면 (T)", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji(name="emoji_22", id=1457645454887096425))
    async def tail_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "T")
