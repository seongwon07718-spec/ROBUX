# --- 약관 동의 뷰 (최종 단계) ---
class AgreementView(discord.ui.View):
    def __init__(self, owner_id, target_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.target_id = target_id
        self.agreed_users = set()

    @discord.ui.button(label="약관 동의하기", style=discord.ButtonStyle.gray)
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. 거래 당사자 확인
        if interaction.user.id not in [self.owner_id, self.target_id]:
            return await interaction.response.send_message("**거래 당사자만 누를 수 있습니다**", ephemeral=True)
        
        # 2. 중복 동의 확인
        if interaction.user.id in self.agreed_users:
            return await interaction.response.send_message("**이미 동의하셨습니다**", ephemeral=True)

        self.agreed_users.add(interaction.user.id)
        
        # 3. 임베드 현황 업데이트 (본문 하단에 표시)
        embed = interaction.message.embeds[0]
        # 기존 설명글 유지하면서 하단에 현황만 업데이트 (기존 현황 텍스트가 쌓이지 않게 처리)
        current_desc = embed.description.split("\n\n**(")[0] # 기존 약관 내용만 추출
        embed.description = f"{current_desc}\n\n**({len(self.agreed_users)}/2) 동의 완료**"
        
        if len(self.agreed_users) >= 2:
            # 두 명 모두 동의 완료 시
            button.disabled = True
            button.style = discord.ButtonStyle.green
            button.label = "동의 완료"
            
            # 버튼 상태 변경 반영
            await interaction.response.edit_message(embed=embed, view=self)
            
            # 최종 완료 임베드 전송
            final_embed = discord.Embed(
                title="약관 동의 완료",
                description="**두 분 모두 약관에 동의하셨습니다\n이제 봇이 아이템을 전달받을 준비를 합니다**",
                color=0xffffff
            )
            await interaction.followup.send(embed=final_embed)
        else:
            # 한 명만 동의했을 때 (1/2 표시)
            await interaction.response.edit_message(embed=embed, view=self)
