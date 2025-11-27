# 커스텀 이모지 정의 (disnake.PartialEmoji 객체)
custom_emoji11 = PartialEmoji(name="47311ltc", id=1438899347453509824)
custom_emoji12 = PartialEmoji(name="6798bnb", id=1438899349110390834)
custom_emoji13 = PartialEmoji(name="tron", id=1438899350582591701)
custom_emoji14 = PartialEmoji(name="7541tetherusdt", id=1439510997730721863)

class CoinDropdown(disnake.ui.Select):
    def __init__(self): # 'init'을 '__init__'으로 수정
        options = [
            disnake.SelectOption(label="USDT", description="테더", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인", value="bnb", emoji=custom_emoji12)
        ]
        super().__init__(placeholder="송금할 코인을 선택해주세요", options=options)

    async def callback(self, interaction: disnake.MessageInteraction):
        try:
            # Avoid timeout by deferring first
            await interaction.response.defer(ephemeral=True)
            user_data = get_verified_user(interaction.author.id)
            if not user_data:
                embed = disnake.Embed(
                    title="오류",
                    description="인증되지 않은 고객님입니다.",
                    color=0xff6200
                )
                await interaction.edit_original_response(embed=embed, ephemeral=True)
                return

            # 최소송금 금액 안내
            selected_coin = self.values[0]

            # 실시간 최소 송금 금액 조회
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
            await interaction.edit_original_response(embed=embed, view=view)
        except Exception:
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0xff6200
            )
            try:
                await interaction.edit_original_response(embed=embed)
            except:
                pass

class NetworkDropdown(disnake.ui.Select):
    def __init__(self, selected_coin): # 'init'을 '__init__'으로 수정
        self.selected_coin = selected_coin

        # 코인별 지원 네트워크
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
        except Exception:
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0x26272f
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                try:
                    await interaction.edit_original_response(embed=embed)
                except Exception:
                    pass
