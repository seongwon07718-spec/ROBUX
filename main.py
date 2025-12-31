# --- 거래 정보 입력 모달 (필수 입력 해제 및 데이터 보존) ---
class InfoModal(discord.ui.Modal, title="거래 정보 입력"):
    # required=False로 설정하여 자기 것만 적을 수 있게 함
    seller = discord.ui.TextInput(label="판매자 닉네임", placeholder="본인이 판매자라면 입력...", required=False)
    buyer = discord.ui.TextInput(label="구매자 닉네임", placeholder="본인이 구매자라면 입력...", required=False)

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
        # 기존에 입력된 값이 있다면 모달창에 미리 표시
        if self.original_view.seller_nick: self.seller.default = self.original_view.seller_nick
        if self.original_view.buyer_nick: self.buyer.default = self.original_view.buyer_nick

    async def on_submit(self, interaction: discord.Interaction):
        # 입력된 값이 있을 때만 업데이트 (비워두면 기존 값 유지)
        if self.seller.value: self.original_view.seller_nick = self.seller.value
        if self.buyer.value: self.original_view.buyer_nick = self.buyer.value
        
        # 판매자와 구매자 정보가 모두 존재할 때만 '계속진행' 버튼 활성화
        if self.original_view.seller_nick and self.original_view.buyer_nick:
            for child in self.original_view.children:
                if child.label == "계속진행":
                    child.disabled = False
        
        embed = discord.Embed(title="📝 거래 상세 정보", color=0xffffff)
        embed.add_field(name="판매자", value=f"```{self.original_view.seller_nick or '미입력'}```", inline=True)
        embed.add_field(name="구매자", value=f"```{self.original_view.buyer_nick or '미입력'}```", inline=True)
        
        status_text = "둘 다 입력되면 버튼이 활성화됩니다."
        if not (self.original_view.seller_nick and self.original_view.buyer_nick):
            status_text = "⚠️ 판매자와 구매자 닉네임을 모두 입력해야 진행 가능합니다."
        
        embed.description = f"**진행 현황: ({len(self.original_view.confirmed_users)}/2) 확인 완료**\n\n{status_text}"
        
        await interaction.response.edit_message(embed=embed, view=self.original_view)

# --- 유저 ID 입력 시 자동 초대 로직 (10초 삭제 추가) ---
# MyBot 클래스 내의 on_message 함수만 이 내용으로 교체하세요.
async def on_message(self, message):
    if message.author.bot: return
    if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("중개-"):
        if message.content.isdigit() and 17 <= len(message.content) <= 20:
            try:
                target_user = await message.guild.fetch_member(int(message.content))
                await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                await message.channel.edit(topic=f"invited:{target_user.id}")
                
                # 10초 뒤 자동 삭제
                await message.channel.send(
                    embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다**", color=0xffffff),
                    delete_after=10.0 
                )
                await message.delete(delay=10.0) # 입력한 ID 메시지도 삭제
            except:
                pass
    await self.process_commands(message)
