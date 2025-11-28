import disnake
import random # 예시를 위한 임시 import

# --- 임시 함수 및 변수 (실제 환경에 맞게 조정 필요) ---
custom_emoji11 = "🪙" # LTC
custom_emoji12 = "💰" # BNB
custom_emoji13 = "⛓️" # TRX
custom_emoji14 = "💵" # USDT

def get_verified_user(user_id):
    # 실제 DB 조회 로직으로 대체해야 합니다.
    # (user_id, name, ..., balance) 형태를 가정
    if random.random() > 0.1: # 90% 확률로 인증된 사용자
        return [user_id, "TestUser", "...", "...", "...", "...", 500000] # 잔액 50만원 가정
    return None

def get_minimum_amounts_krw():
    # 실제 최소 금액 조회 로직으로 대체해야 합니다.
    return {'USDT': 10000, 'TRX': 5000, 'LTC': 1968, 'BNB': 20000}

# 모달 클래스 정의 (예시)
class AmountModal(disnake.ui.Modal):
    def __init__(self, network, coin):
        self.network = network
        self.coin = coin
        components = [
            disnake.ui.TextInput(
                label="송금 금액 (KRW)",
                custom_id="amount",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="출금 주소",
                custom_id="address",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=100
            )
        ]
        # custom_id에 정보를 담아 handle_amount_modal로 전달
        super().__init__(
            title=f"{coin.upper()} | {network} 송금 신청",
            custom_id=f"amount_modal_{network}_{coin}",
            components=components
        )

# ----------------------------------------------------

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
        # 🚨 상호작용 실패 방지를 위해 최대한 빨리 defer 호출
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            # 첫 defer 시도에서 실패하면 로직 진행 불가 (이 경우는 드물지만, 방어적 코딩)
            print(f"CoinDropdown defer 실패: {e}")
            return

        try:
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
            # DB/API 호출 시 지연 발생 가능 -> defer로 3초 제한 회피
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
            # defer 했으므로 followup.send 사용
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            print(f"CoinDropdown callback 에러: {e}")
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0xff6200
            )
            # 이미 defer 되었으므로 followup으로 예외 메시지 전송
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
            # 🚨 모달 호출은 즉시 응답이므로 defer 금지. 3초 이내에 호출되어야 합니다.
            # 모달 호출에 실패하면 '상호작용 실패' 발생
            await interaction.response.send_modal(AmountModal(self.values[0], self.selected_coin))
        except Exception as e:
            print(f"NetworkDropdown callback 예외 발생: {e}")
            embed = disnake.Embed(
                title="오류",
                description="처리 중 오류가 발생했습니다.",
                color=0xff6200 # 오류색 통일
            )
            try:
                # 🚨 response를 사용했으면 이 호출은 실패할 가능성이 높지만,
                # send_modal이 실패한 경우 (response를 사용하지 않은 경우) followup으로 응답
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass

# 대기중인 거래 정보를 저장하는 딕셔너리
pending_transactions = {}

async def handle_amount_modal(interaction: disnake.ModalInteraction):
    try:
        # 응답 지연 (3초 제한 해결). 모달 제출 후 로직은 시간이 걸릴 수 있으므로 필수.
        await interaction.response.defer(ephemeral=True)

        amount_str = interaction.text_values.get("amount", "").strip()
        address = interaction.text_values.get("address", "").strip()

        if not amount_str or not address:
            embed = disnake.Embed(
                title="오류",
                description="모든 필드를 입력해주세요.",
                color=0xff6200
            )
            # 🚨 defer 후 에러 메시지 전송은 edit_original_response 대신 followup.send 사용 (더 안정적)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # ... (이하 로직은 krw_amount_input 변수명 통일 및 오류 처리 안정성 확보를 위해 수정)

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
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        custom_id_parts = interaction.custom_id.split('_')
        # custom_id: amount_modal_{network}_{coin}
        network = custom_id_parts[-2] if len(custom_id_parts) >= 3 else "bep20"
        coin = custom_id_parts[-1] if len(custom_id_parts) >= 4 else "usdt"

        min_amounts_krw = get_minimum_amounts_krw()
        min_amount_krw = min_amounts_krw.get(coin.upper(), 10000)
        coin_unit = coin.upper()

        if krw_amount_input < min_amount_krw:
            embed = disnake.Embed(
                title="**오류**",
                description=f"**출금 최소 금액은 {min_amount_krw:,}원입니다.**",
                color=0xff6200
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        user_data = get_verified_user(interaction.author.id)
        if not user_data:
            embed = disnake.Embed(
                title="**오류**",
                description="**인증되지 않은 고객님 입니다.**",
                color=0xff6200
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        current_balance = user_data[6] if len(user_data) > 6 else 0
        if current_balance < krw_amount_input:
            embed = disnake.Embed(
                title="잔액 부족",
                description=f"보유 금액 = {current_balance:,}원\n필요금액: {int(krw_amount_input):,}원",
                color=0xff6200
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- 송금 처리 로직 (생략) ---
        success_embed = disnake.Embed(
            title="✅ 송금 신청 완료",
            description=f"**{int(krw_amount_input):,}원** ({coin_unit}) 송금 요청이 접수되었습니다.",
            color=0x00ff00
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)


    except Exception as e:
        print(f"handle_amount_modal 예외 발생: {e}")
        error_embed = disnake.Embed(
            title="오류",
            description="송금 처리 중 알 수 없는 오류가 발생했습니다.",
            color=0xff6200
        )
        try:
            # 🚨 이미 defer 했으므로 followup으로 최종 오류 메시지 전송
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception:
            pass
