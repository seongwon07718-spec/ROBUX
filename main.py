class NetworkDropdown(disnake.ui.Select):
    def __init__(self, selected_coin):
        self.selected_coin = selected_coin

        network_options = {
            'usdt': [
                disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20"),
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'trx': [
                disnake.SelectOption(label="TRC20", description="TRON Network", value="trc20")
            ],
            'ltc': [
                disnake.SelectOption(label="LTC", description="Litecoin Network", value="ltc")
            ],
            'bnb': [
                disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")
            ]
        }

        options = network_options.get(selected_coin.lower(), [
            disnake.SelectOption(label="BEP20", description="BSC Network", value="bep20")
        ])

        super().__init__(placeholder="네트워크를 선택해주세요", options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        try:
            # 모달 호출은 반드시 즉시 보내야 하므로 defer() 금지
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 예외 발생: {e}")
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0x26272f
            )
            try:
                # 이미 response를 사용했거나 예외 발생 시 followup으로 응답
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass
