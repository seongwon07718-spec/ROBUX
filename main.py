async def on_submit(self, interaction: discord.Interaction):
    try:
        amount = float(self.amount.value)
        amount_needed_krw, amount_after_fee_krw = calculate_fees(amount, self.is_dollar)

        embed = discord.Embed(title="수수료 계산 결과", color=0xffffff)
        embed.add_field(
            name=f"{amount:,.2f} {'달러(USD)' if self.is_dollar else '원(KRW)'}이 있다면",
            value=f"최종적으로 약 `{amount_after_fee_krw:,.2f}` 원을 송금 받을 수 있습니다.", inline=False
        )
        embed.add_field(
            name=f"원하는 금액을 `{amount:,.2f}` {'달러(USD)' if self.is_dollar else '원(KRW)'}만큼 받는다면",
            value=f"약 `{amount_needed_krw:,.2f}` 원이 필요합니다.", inline=False
        )

        embed.set_footer(text=f"실시간 김프 값과 {FEE_RATE*100:.1f}% 수수료가 적용되어 계산되었습니다.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except ValueError:
        # 여기서도 항상 한번만 응답하도록 합니다.
        if interaction.response.is_done():
            await interaction.followup.send("❌ 유효한 숫자를 입력해주세요.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 유효한 숫자를 입력해주세요.", ephemeral=True)
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ 계산 중 오류가 발생했습니다: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 계산 중 오류가 발생했습니다: {e}", ephemeral=True)
