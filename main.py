# bot.py
import os, random, logging, math
from datetime import datetime
import disnake
from disnake.ext import commands, tasks

# 내부 모듈
import helpers_db
import explorer_api
import api

# 설정 (여기에 직접 넣어 실행)
TOKEN = "여기에_디스코드_봇_토큰을_넣으세요"
CHANNEL_ADMIN_ID = 1436602243905228831  # 관리자 알림 채널 ID (예시)
# BscScan 키는 explorer_api 파일에 설정하세요 (explorer_api.BSCSCAN_API_KEY)

# 로거
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB 초기화
helpers_db.init_db()

intents = disnake.Intents.default()
bot = commands.Bot(command_prefix='/', intents=intents)

# Modal 정의 (은행/주소/TXID)
class BankModal(disnake.ui.Modal):
    def __init__(self, serial_code):
        components = [
            disnake.ui.TextInput(label="은행명", placeholder="예: 토스뱅크", custom_id="bank_name"),
            disnake.ui.TextInput(label="계좌번호", placeholder="예: 1001-2440-7138", custom_id="account_number")
        ]
        super().__init__(title="계좌 추가", custom_id=f"bank_modal_{serial_code}", components=components)

class CoinAddressModal(disnake.ui.Modal):
    def __init__(self, coin, serial_code):
        components = [ disnake.ui.TextInput(label=f"{coin} 주소", placeholder="지갑 주소 입력", custom_id="coin_address") ]
        super().__init__(title=f"{coin} 주소 설정", custom_id=f"coinaddr_modal_{coin}_{serial_code}", components=components)
        self.coin = coin

class TxidModal(disnake.ui.Modal):
    def __init__(self, coin, serial_code):
        components = [ disnake.ui.TextInput(label="TXID 입력", placeholder="TXID 입력", custom_id="txid_value") ]
        super().__init__(title="TXID 전송", custom_id=f"txid_modal_{coin}_{serial_code}", components=components)
        self.coin = coin

# /매입패널
@bot.slash_command(name="매입패널", description="코인 매입 패널을 엽니다")
async def buy_panel(inter):
    try:
        krw_rate = api.get_exchange_rate()
        prices = {}
        for c in ['USDT','BNB','TRX','LTC','DOGE','SOL']:
            prices[c] = api.get_coin_price(c)
        price_text = ""
        for coin, usd in prices.items():
            price_text += f"{coin}: ₩{int(usd*krw_rate):,}\n"
        embed = disnake.Embed(title="코인 매입 패널", color=0x00b894)
        embed.add_field(name="USD→KRW 환율", value=f"₩{int(krw_rate):,}", inline=False)
        embed.add_field(name="실시간 시세(KRW)", value=price_text, inline=False)
        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="매입하기", custom_id="open_buy_embed"))
        await inter.response.send_message(embed=embed, view=view)
    except Exception as e:
        logger.exception(e)
        await inter.response.send_message("오류 발생", ephemeral=True)

# /코인주소설정
@bot.slash_command(name="코인주소설정", description="코인별 주소 등록")
async def coin_addr_setup(inter):
    view = disnake.ui.View()
    class AddrSelect(disnake.ui.Select):
        def __init__(self):
            options = [ disnake.SelectOption(label=c, value=c) for c in ["LTC","BNB","USDT","TRX","DOGE","SOLANA"] ]
            super().__init__(placeholder="설정할 코인을 선택하세요", min_values=1, max_values=1, options=options, custom_id="addr_select")
        async def callback(self, select_inter):
            coin = select_inter.values[0]
            serial = random.randint(100000,999999)
            await select_inter.response.send_modal(CoinAddressModal(coin, serial))
    view.add_item(AddrSelect())
    await inter.response.send_message("설정할 코인을 선택하세요.", view=view, ephemeral=True)

# 버튼 처리
@bot.event
async def on_button_click(interaction):
    try:
        cid = interaction.component.custom_id

        if cid == "open_buy_embed":
            embed = disnake.Embed(title="계좌 설정", description="계좌 추가 / 계좌 선택 후 코인을 선택하세요.", color=0x0984e3)
            view = disnake.ui.View()
            view.add_item(disnake.ui.Button(label="계좌 추가", custom_id="add_bank", style=disnake.ButtonStyle.green))
            view.add_item(disnake.ui.Button(label="계좌 선택", custom_id="select_bank", style=disnake.ButtonStyle.blurple))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        if cid == "add_bank":
            serial = random.randint(100000,999999)
            await interaction.response.send_modal(BankModal(serial))
            return

        if cid == "select_bank":
            banks = helpers_db.get_user_banks(interaction.author.id)
            if not banks:
                await interaction.response.send_message("등록된 계좌가 없습니다. 먼저 계좌 추가해주세요.", ephemeral=True)
                return
            class BankSelect(disnake.ui.Select):
                def __init__(self):
                    opts = [disnake.SelectOption(label=f"{b['bank_name']} {b['account_number']}", value=str(b['id'])) for b in banks]
                    super().__init__(placeholder="계좌 선택", min_values=1, max_values=1, options=opts, custom_id="bank_select")
                async def callback(self, select_inter):
                    bank_id = int(select_inter.values[0])
                    # 이동: 코인 선택
                    class CoinSelect(disnake.ui.Select):
                        def __init__(self):
                            options = [ disnake.SelectOption(label=c, value=c) for c in ["LTC","BNB","USDT","TRX","DOGE","SOLANA"] ]
                            super().__init__(placeholder="코인 선택", min_values=1, max_values=1, options=options, custom_id=f"buy_coin_select_{bank_id}")
                        async def callback(self, coin_inter):
                            coin = coin_inter.values[0]
                            addr = helpers_db.get_coin_address(coin_inter.author.id, coin)
                            embed2 = disnake.Embed(title=f"{coin} 매입 정보", color=0x00b894)
                            if addr:
                                embed2.add_field(name="등록된 수령주소", value=f"`{addr}`", inline=False)
                            else:
                                embed2.add_field(name="등록된 주소 없음", value="먼저 /코인주소설정 으로 주소를 등록해주세요.", inline=False)
                            view2 = disnake.ui.View()
                            view2.add_item(disnake.ui.Button(label="TXID 전송", custom_id=f"open_tx_modal_{coin}_{bank_id}"))
                            await coin_inter.response.send_message(embed=embed2, view=view2, ephemeral=True)
                    view = disnake.ui.View(); view.add_item(CoinSelect())
                    await select_inter.response.send_message("매입할 코인을 선택하세요.", view=view, ephemeral=True)
            view = disnake.ui.View(); view.add_item(BankSelect())
            await interaction.response.send_message("계좌를 선택하세요.", view=view, ephemeral=True)
            return

        if cid.startswith("open_tx_modal_"):
            # format open_tx_modal_{coin}_{bankid}
            parts = cid.split("_")
            coin = parts[3]
            serial = random.randint(100000,999999)
            await interaction.response.send_modal(TxidModal(coin, serial))
            return

    except Exception as e:
        logger.exception(e)
        try:
            await interaction.response.send_message("버튼 처리 중 오류가 발생했습니다.", ephemeral=True)
        except:
            pass

# 모달 제출 처리
@bot.event
async def on_modal_submit(interaction):
    try:
        cid = interaction.custom_id

        if cid.startswith("bank_modal_"):
            bank_name = interaction.text_values.get("bank_name","").strip()
            acc = interaction.text_values.get("account_number","").strip()
            if not bank_name or not acc:
                await interaction.response.send_message("은행명과 계좌번호 모두 입력해주세요.", ephemeral=True); return
            bid = helpers_db.save_bank_info(interaction.author.id, bank_name, acc)
            await interaction.response.send_message(f"계좌 추가 완료 (ID: {bid})", ephemeral=True)
            return

        if cid.startswith("coinaddr_modal_"):
            parts = cid.split("_"); coin = parts[2]
            addr = interaction.text_values.get("coin_address","").strip()
            if not addr:
                await interaction.response.send_message("주소 입력이 필요합니다.", ephemeral=True); return
            helpers_db.set_coin_address(interaction.author.id, coin, addr)
            await interaction.response.send_message(f"{coin} 주소가 저장되었습니다.", ephemeral=True)
            return

        if cid.startswith("txid_modal_"):
            parts = cid.split("_"); coin = parts[2]
            txid = interaction.text_values.get("txid_value","").strip()
            if not txid:
                await interaction.response.send_message("TXID를 입력해주세요.", ephemeral=True); return

            # 자동조회
            raw = explorer_api.fetch_tx_raw(coin, txid)
            reg_addr = helpers_db.get_coin_address(interaction.author.id, coin)
            bank_list = helpers_db.get_user_banks(interaction.author.id)
            bank_id = bank_list[0]['id'] if bank_list else None

            if not raw:
                rec = helpers_db.save_purchase(interaction.author.id, bank_id, coin, reg_addr, txid, 0.0, status='pending')
                # admin notify
                admin_ch = bot.get_channel(CHANNEL_ADMIN_ID) or await bot.fetch_channel(CHANNEL_ADMIN_ID)
                if admin_ch:
                    aembed = disnake.Embed(title="TX 자동조회 실패(수동확인 필요)", color=0xff0000)
                    aembed.add_field(name="사용자", value=f"{interaction.author} ({interaction.author.id})", inline=False)
                    aembed.add_field(name="코인", value=coin, inline=True)
                    aembed.add_field(name="TXID", value=f"`{txid}`", inline=False)
                    aembed.add_field(name="DB ID", value=str(rec), inline=True)
                    await admin_ch.send(embed=aembed)
                await interaction.response.send_message("자동조회 실패: 운영진이 확인 후 처리합니다.", ephemeral=True)
                return

            # parse standardized response (explorer_api returns structured dict for BSC/TRX cases)
            to_addr = raw.get('to_address') or (raw.get('raw', {}).get('to') if raw.get('raw') else None)
            amount_coin = float(raw.get('amount') or 0.0)
            symbol = raw.get('token_symbol') or coin
            # KRW 환산
            price_usd = api.get_coin_price(symbol)
            krw = api.get_exchange_rate()
            amount_krw = amount_coin * price_usd * krw

            match = (reg_addr and to_addr and reg_addr.lower() == to_addr.lower())

            rec = helpers_db.save_purchase(interaction.author.id, bank_id, coin, to_addr, txid, amount_krw, 'KRW', status='confirmed' if match else 'pending')

            # admin embed
            admin_ch = bot.get_channel(CHANNEL_ADMIN_ID) or await bot.fetch_channel(CHANNEL_ADMIN_ID)
            if admin_ch:
                aembed = disnake.Embed(title="매입 자동확인" if match else "매입 자동접수(주소 불일치 가능)", color=0x00b894 if match else 0xffa500)
                aembed.add_field(name="사용자", value=f"{interaction.author} ({interaction.author.id})", inline=False)
                aembed.add_field(name="코인", value=symbol, inline=True)
                aembed.add_field(name="보낸 수량", value=f"{amount_coin} {symbol}", inline=True)
                aembed.add_field(name="환산 KRW", value=f"₩{int(amount_krw):,}", inline=False)
                aembed.add_field(name="수신주소", value=f"`{to_addr}`", inline=False)
                aembed.add_field(name="등록주소 일치", value=str(match), inline=True)
                aembed.add_field(name="TXID", value=f"`{txid}`", inline=False)
                aembed.set_footer(text=f"DB ID:{rec} / {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                await admin_ch.send(embed=aembed)

            # 사용자 알림: 얼마를 더 입금해야 하는지 알려줌 (수수료 0%)
            # 예시: 사용자가 사전 입력한 목표 KRW 값이 없으므로, 자동조회된 금액을 안내
            if match:
                await interaction.response.send_message(f"입금 확인됨: 약 ₩{int(amount_krw):,} 입금되었습니다.", ephemeral=True)
            else:
                await interaction.response.send_message("입금이 접수되었으나 등록된 주소와 일치하지 않습니다. 운영자 확인 후 처리됩니다.", ephemeral=True)
            return

    except Exception as e:
        logger.exception(e)
        try:
            await interaction.response.send_message("처리 중 오류가 발생했습니다.", ephemeral=True)
        except:
            pass

# 시작
if __name__ == "__main__":
    bot.run(TOKEN)
