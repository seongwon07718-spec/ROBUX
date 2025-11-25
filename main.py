class AmountModal(disnake.ui.Modal):
    def __init__(self, network, coin='usdt'):
        self.network = network
        self.coin = coin

        min_amounts_krw = get_minimum_amounts_krw()
        min_krw = min_amounts_krw.get(coin.upper(), 10000)

        components = [
            disnake.ui.TextInput(
                label="금액",
                placeholder=f"금액을 입력해주세요 (최소 {min_krw:,}원)",
                custom_id="amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=15,
            ),
            disnake.ui.TextInput(
                label="코인 주소",
                placeholder="송금 받으실 지갑 주소를 입력해주세요",
                custom_id="address",
                style=disnake.TextInputStyle.short,
                min_length=10,
                max_length=100,
            )
        ]
        super().__init__(
            title=f"{coin.upper()} 송금 정보",
            custom_id=f"amount_modal_{network}_{coin}",
            components=components,
        )


class CoinDropdown(disnake.ui.Select):
    def __init__(self):
        options = [
            disnake.SelectOption(label="USDT", description="테더코인 선택", value="usdt", emoji=custom_emoji14),
            disnake.SelectOption(label="TRX", description="트론 선택", value="trx", emoji=custom_emoji13),
            disnake.SelectOption(label="LTC", description="라이트코인 선택", value="ltc", emoji=custom_emoji11),
            disnake.SelectOption(label="BNB", description="바이낸스코인 선택", value="bnb", emoji=custom_emoji12)
        ]
        super().__init__(placeholder="송금할 코인을 선택해주세요", options=options)


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
