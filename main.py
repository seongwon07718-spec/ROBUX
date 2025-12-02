# /수수료계산 슬래시 커맨드
@app_commands.command(name="수수료계산", description="수수료를 포함한 송금 금액을 계산합니다.")
async def calculate_fee_command(self, interaction: discord.Interaction):
    embed = discord.Embed(
        title="❄ 수수료 계산기", 
        description="계산할 금액의 단위를 선택해주세요!", 
        color=discord.Color.blue()
    )
    embed.set_footer(text="계산 중 약간의 오차가 발생할 수 있습니다.")
    
    view = CalculatorView(ALLOWED_USER_IDS) 
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True) # <--- 여기가 임베드와 버튼을 같이 보내는 부분입니다!
