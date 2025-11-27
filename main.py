class CoinDropdown(disnake.ui.Select):
    def __init__(self):
        options = [
            disnake.SelectOption(label="USDT", description="테더", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인", value="bnb", emoji=custom_emoji12)
        ]
        super().__init__(placeholder="송금할 코인을 선택해주세요", options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        try:
            await interaction.response.defer(ephemeral=True)
            user_data = get_verified_user(interaction.author.id)
            if not user_data:
                embed = disnake.Embed(
                    title="오류",
                    description="인증되지 않은 고객님입니다.",
                    color=0xff6200
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            selected_coin = self.values[0]
            min_amounts_krw = get_minimum_amounts_krw()
            min_krw = min_amounts_krw.get(selected_coin.upper(), 10000)
            min_amount = f"{min_krw:,}"
                
            embed = disnake.Embed(
                title=f"{selected_coin.upper()} 송금",
                description=f"최소 송금 금액 = {min_amount}원",
                color=0xffffff
            )
            view = disnake.ui.View()
            view.add_item(NetworkDropdown(selected_coin))
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"CoinDropdown callback 에러: {e}")
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0xff6200
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass

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
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 에러: {e}")
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0x26272f
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass
