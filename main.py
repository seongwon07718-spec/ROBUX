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
                description=f"**최소 송금 금액 = {min_amount}원**",
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

# 대기중인 거래 정보를 저장하는 딕셔너리
pending_transactions = {}

async def handle_amount_modal(interaction: disnake.ModalInteraction):
    try:
        # 응답 지연 (3초 제한 해결)
        await interaction.response.defer(ephemeral=True)

        amount_str = interaction.text_values.get("amount", "").strip()
        address = interaction.text_values.get("address", "").strip()

        if not amount_str or not address:
            embed = disnake.Embed(
                title="오류",
                description="모든 필드를 입력해주세요.",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return

        try:
            krw_amount_input = float(amount_str) # 사용자가 입력한 KRW 금액
            if krw_amount_input <= 0:
                raise ValueError("양수여야 합니다")
        except (ValueError, TypeError):
            embed = disnake.Embed(
                title="**오류**",
                description="**올바른 숫자를 입력해주세요.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return

        # 커스텀 ID에서 코인과 네트워크 정보 추출
        custom_id_parts = interaction.custom_id.split('_')
        network = custom_id_parts[-2] if len(custom_id_parts) >= 3 else "bep20"
        coin = custom_id_parts[-1] if len(custom_id_parts) >= 4 else "usdt"

        # 통일된 최소 송금 금액 조회
        min_amounts_krw = get_minimum_amounts_krw()
        min_amount_krw = min_amounts_krw.get(coin.upper(), 10000)
        coin_unit = coin.upper()

        if krw_amount_input < min_amount_krw:
            embed = disnake.Embed(
                title="**오류**",
                description=f"**출금 최소 금액은 {min_amount_krw:,}원입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return

        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**인증되지 않은 고객님 입니다.**",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return

        current_balance = user_data[6] if len(user_data) > 6 else 0
        if current_balance < krw_amount_input:
            embed = disnake.Embed(
                title="잔액 부족",
                description=f"보유 금액 = {current_balance:,}원\n필요금액: {int(krw_amount_input):,}원",
                color=0xff6200
            )
            await interaction.edit_original_response(embed=embed)
            return
