# --- 거래 단계 뷰 ---
class TradeStepView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.confirmed_users = set()
        self.seller_nick = "미입력"
        self.buyer_nick = "미입력"
        self.confirm_trade_button.disabled = True

    @discord.ui.button(label="거래정보 수정", style=discord.ButtonStyle.secondary)
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoModal(self))

    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray) 
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        if interaction.user.id in self.confirmed_users:
            return await interaction.response.send_message("**이미 확인 버튼을 누르셨습니다**", ephemeral=True)

        self.confirmed_users.add(interaction.user.id)
        
        # 현황 업데이트 (1/2 -> 2/2)
        embed = interaction.message.embeds[0]
        embed.description = f"**({len(self.confirmed_users)}/2) 확인 완료**"

        if len(self.confirmed_users) >= 2:
            # 2/2가 되었을 때
            for child in self.children:
                child.disabled = True
            # 먼저 2/2로 바뀐 임베드와 비활성화된 버튼을 보여줌
            await interaction.response.edit_message(embed=embed, view=self)

            # 그 후 약관 임베드 전송
            agree_embed = discord.Embed(
                title="중개 이용 약관",
                description=("**제 1조 [중개 원칙]\n┗ 판매자와 구매자 사이의 안전한 거래를 돕기 위한 봇입니다\n┗ 모든 거래 과정(채팅, 아이템 전달)은 서버 데이터 베이스에 실시간으로 저장됩니다\n\n제 2조 [아이템 및 대금 보관]\n┗ 판매자는 약관 동의 후 저장된 중개 전용 계정으로 템을 전달 해야합니다\n┗ 구매자는 중개인이 아이템 수령을 확인한 후에만 대금을 송금 해야 합니다\n┗ 임의로 개인 간 거래를 진행하여 발생하는 사고는 본 서버가 책임지지 않습니다\n\n제 3조 [거래 취소 및 환불]\n┗ 봇이 아이템을 수령하기 전에는 양측 합의 하에 자유롭게 취소 가능합니다\n┗ 봇이 아이템을 수령한 후에는 단심 변심으로 인한 취소가 불가능하며, 상대방의 동의가 있어야만 반환됩니다\n\n제 4조 [금지 사항]\n┗ 아이템 수량 속임수, 송금 확인증 조작 등의 기만행위 적발 시 즉시 영구 밴 처리됩니다\n┗ 중개 과정 중 욕설, 도배, 거래 방해 행위는 제재 대상입니다\n\n제 5조 [면책 조항]\n┗ 로블록스 자페 시스템 오류나 서버 점검으로 인한 아이템 증발에 대해서는 복구가 불가능할 수 있습니다\n┗ 이용자는 본 약관 동의 버튼을 누름으로써 위 모든 내용에 동의한 것으로 간주합니다**"),
                color=0xffffff
            )
            agree_embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455922358417358848/IMG_0741.png")
            
            await interaction.followup.send(embed=agree_embed, view=AgreementView(self.owner_id, self.target_id))
        else:
            # 1/2일 때
            await interaction.response.edit_message(embed=embed, view=self)
