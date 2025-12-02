class FeeModal(discord.ui.Modal, title="수수료 계산"):
    def __init__(self, is_dollar: bool):
        super().__init__()
        self.is_dollar = is_dollar

        label = "달러" if is_dollar else "원화"
        placeholder = f"계산할 금액을 {label} 기준으로 입력해주세요."
        
        self.amount = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            required=True,
            max_length=20,
            style=discord.TextStyle.short
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 입력값 전처리: 공백 제거 + 단위(원,달러) + 콤마 제거
            cleaned = self.amount.value.strip().replace("원", "").replace("달러", "").replace(",", "")
            amount = float(cleaned)
            
            # 수수료 및 김치프리미엄 계산 함수 호출
            amount_needed, amount_after_fee = calculate_fees(amount, self.is_dollar)

            embed = discord.Embed(title="수수료 계산 결과", color=0xffffff)
            embed.add_field(
                name=f"{amount:,.2f} {'달러(USD)' if self.is_dollar else '원(KRW)'}이 있다면",
                value=f"최종적으로 약 `{amount_after_fee:,.2f}` 원을 송금 받을 수 있습니다.", inline=False
            )
            embed.add_field(
                name=f"원하는 금액을 `{amount:,.2f}` {'달러(USD)' if self.is_dollar else '원(KRW)'}만큼 받는다면",
                value=f"약 `{amount_needed:,.2f}` 원이 필요합니다.", inline=False
            )
            embed.set_footer(text=f"실시간 김프 값과 {FEE_RATE*100:.1f}% 수수료가 적용되었습니다.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except ValueError:
            # 입력값이 숫자가 아닐 때
            if interaction.response.is_done():
                await interaction.followup.send("❌ 숫자만 입력해주세요. 예) 5000", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 숫자만 입력해주세요. 예) 5000", ephemeral=True)

        except Exception as e:
            # 그 외 예외 처리
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ 계산 중 오류가 발생했습니다: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ 계산 중 오류가 발생했습니다: {e}", ephemeral=True)
