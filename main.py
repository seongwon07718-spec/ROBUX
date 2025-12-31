# --- 약관 동의 뷰 (최종 단계) ---
class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.green, emoji="✅")
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 거래 당사자 확인
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        # 중복 동의 확인
        if interaction.user.id in self.agreed_users:
            return await interaction.response.send_message("**이미 동의하셨습니다**", ephemeral=True)

        self.agreed_users.add(interaction.user.id)
        
        if len(self.agreed_users) >= 2:
            # 두 명 모두 동의 완료
            button.disabled = True
            await interaction.response.edit_message(view=self)
            
            final_embed = discord.Embed(
                title="✅ 약관 동의 완료",
                description="**두 분 모두 약관에 동의하셨습니다.\n관리자가 확인 후 다음 단계를 안내해 드릴 예정입니다.**",
                color=0x00ff00
            )
            await interaction.followup.send(embed=final_embed)
        else:
            # 한 명만 동의했을 때
            await interaction.response.send_message(f"**{interaction.user.mention}님이 약관에 동의하셨습니다. (1/2)**", ephemeral=False)

# --- TradeStepView 내 계속진행 버튼 로직 ---
# TradeStepView 클래스 안의 confirm_trade_button 함수를 아래로 교체하세요.
    @discord.ui.button(label="계속진행", style=discord.ButtonStyle.gray)
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        if interaction.user.id in self.confirmed_users:
            return await interaction.response.send_message("**이미 확인 버튼을 누르셨습니다**", ephemeral=True)

        self.confirmed_users.add(interaction.user.id)
        
        if len(self.confirmed_users) >= 2:
            # 기존 정보 확인 버튼 비활성화
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)

            # 약관 동의 임베드 전송
            agree_embed = discord.Embed(
                title="📜 중개 이용 약관",
                description=(
                    "**거래를 진행하시기 전 아래 내용을 반드시 숙지해 주세요.**\n\n"
                    "1. 모든 거래 과정은 관리자에 의해 모니터링됩니다.\n"
                    "2. 약관 동의 후에는 중개 절차에 적극 협조해야 합니다.\n"
                    "3. 허위 정보 입력 시 제재를 받을 수 있습니다.\n\n"
                    "**내용에 동의하신다면 아래 [약관 동의하기] 버튼을 눌러주세요.**"
                ),
                color=0xffffff
            )
            agree_embed.set_image(url="https://cdn.discordapp.com/attachments/1455759161039261791/1455875683703193711/IMG_0728.png")
            
            # 약관 동의 버튼이 담긴 AgreementView 전송
            await interaction.followup.send(
                embed=agree_embed, 
                view=AgreementView(self.owner_id, self.target_id)
            )
        else:
            # 한 명만 확인했을 때
            embed = interaction.message.embeds[0]
            embed.description = f"**진행 현황 = ({len(self.confirmed_users)}/2) 확인 완료**"
            await interaction.response.edit_message(embed=embed, view=self)
