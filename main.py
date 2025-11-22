import os
import random
import sqlite3
import logging
import math
from datetime import datetime

import disnake
from disnake.ext import commands, tasks

# ===== 설정 (여기서 바로 토큰 넣어 실행 가능) =====
TOKEN = "여기에_디스코드_봇_토큰을_넣으세요"
# 관리자 로그 채널 ID(예시) - 실제 채널 ID로 바꿔주세요
CHANNEL_CHARGE_LOG = 1436602243905228831

# ===== 로거 설정 =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== DB 헬퍼 (동일 로직으로 재사용) =====
DB_PATH = 'DB/buy_panel.db'
os.makedirs('DB', exist_ok=True)

def save_bank_info(user_id, bank_name, account_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO bank_accounts (user_id, bank_name, account_number, created_at) VALUES (?, ?, ?, ?)',
              (user_id, bank_name, account_number, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    bid = c.lastrowid
    conn.close()
    return bid

def get_latest_bank(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, bank_name, account_number, created_at FROM bank_accounts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def set_coin_address(user_id, coin, address):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO coin_addresses (user_id, coin, address, created_at) VALUES (?, ?, ?, ?)',
              (user_id, coin.upper(), address, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_coin_address(user_id, coin):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT address FROM coin_addresses WHERE user_id = ? AND coin = ?', (user_id, coin.upper()))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_purchase_record(user_id, bank_id, coin, address, txid, amount, currency='KRW', status='pending'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO purchases (user_id, bank_id, coin, address, txid, amount, currency, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (user_id, bank_id, coin.upper() if coin else None, address, txid, amount, currency, status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    rec_id = c.lastrowid
    conn.close()
    return rec_id

# ===== Bot 초기화 =====
intents = disnake.Intents.default()
bot = commands.Bot(command_prefix='/', intents=intents)

# ===== Modal 정의 =====
class BankModal(disnake.ui.Modal):
    def __init__(self, serial_code):
        components = [
            disnake.ui.TextInput(label="은행명", placeholder="예: 토스뱅크", custom_id="bank_name"),
            disnake.ui.TextInput(label="계좌번호", placeholder="예: 1001-2440-7138", custom_id="account_number")
        ]
        super().__init__(title="계좌 설정", custom_id=f"bank_modal_{serial_code}", components=components)

class CoinAddressModal(disnake.ui.Modal):
    def __init__(self, coin, serial_code):
        components = [
            disnake.ui.TextInput(label=f"{coin} 주소", placeholder="지갑 주소를 입력하세요", custom_id="coin_address")
        ]
        super().__init__(title=f"{coin} 주소 설정", custom_id=f"coinaddr_modal_{coin}_{serial_code}", components=components)
        self.coin = coin

class TxidModal(disnake.ui.Modal):
    def __init__(self, coin, serial_code):
        components = [
            disnake.ui.TextInput(label="TXID 입력", placeholder="TXID를 입력하세요", custom_id="txid_value")
        ]
        super().__init__(title="TXID 전송", custom_id=f"txid_modal_{coin}_{serial_code}", components=components)
        self.coin = coin

# ===== 슬래시 명령어: 매입패널 =====
@bot.slash_command(name="매입패널", description="코인 매입 패널을 엽니다")
async def buy_panel(inter):
    embed = disnake.Embed(title="코인 매입 패널", description="아래 버튼을 눌러 매입을 시작하세요.", color=0x00b894)
    embed.add_field(name="지원 코인", value="LTC, BNB, USDT, TRX, DOGE, SOLANA", inline=False)
    view = disnake.ui.View()
    buy_btn = disnake.ui.Button(label="매입하기", style=disnake.ButtonStyle.gray, custom_id="open_buy_bank_modal")
    view.add_item(buy_btn)
    await inter.response.send_message(embed=embed, view=view)

# ===== 슬래시 명령어: 코인주소설정 =====
@bot.slash_command(name="코인주소설정", description="코인별 입금(수령) 주소를 등록합니다")
async def coin_addr_setup(inter):
    view = disnake.ui.View()
    class AddrSelect(disnake.ui.Select):
        def __init__(self):
            options = [
                disnake.SelectOption(label="LTC", value="LTC"),
                disnake.SelectOption(label="BNB", value="BNB"),
                disnake.SelectOption(label="USDT", value="USDT"),
                disnake.SelectOption(label="TRX", value="TRX"),
                disnake.SelectOption(label="DOGE", value="DOGE"),
                disnake.SelectOption(label="SOLANA", value="SOLANA")
            ]
            super().__init__(placeholder="설정할 코인을 선택하세요", min_values=1, max_values=1, options=options, custom_id="addr_select")
        async def callback(self, select_inter):
            coin = select_inter.values[0]
            serial = random.randint(100000,999999)
            await select_inter.response.send_modal(CoinAddressModal(coin, serial))
    view.add_item(AddrSelect())
    await inter.response.send_message("설정할 코인을 선택하세요.", view=view, ephemeral=True)

# ===== 버튼 이벤트 처리 =====
@bot.event
async def on_button_click(interaction):
    try:
        cid = interaction.component.custom_id

        if cid == "open_buy_bank_modal":
            serial = random.randint(100000, 999999)
            await interaction.response.send_modal(BankModal(serial))
            return

        if cid.startswith("open_tx_modal_"):
            coin = cid.split("_")[-1]
            serial = random.randint(100000,999999)
            await interaction.response.send_modal(TxidModal(coin, serial))
            return

    except Exception as e:
        logger.exception(f"on_button_click 오류: {e}")
        try:
            await interaction.response.send_message("버튼 처리 중 오류가 발생했습니다.", ephemeral=True)
        except:
            pass

# ===== 모달 제출 처리 =====
@bot.event
async def on_modal_submit(interaction):
    try:
        cid = interaction.custom_id

        if cid.startswith("bank_modal_"):
            bank_name = interaction.text_values.get("bank_name", "").strip()
            account_number = interaction.text_values.get("account_number", "").strip()
            if not bank_name or not account_number:
                await interaction.response.send_message("은행명과 계좌번호를 모두 입력해주세요.", ephemeral=True)
                return
            bank_id = save_bank_info(interaction.author.id, bank_name, account_number)

            embed = disnake.Embed(title="매입할 코인을 선택하세요", description="드롭다운에서 코인을 선택하세요.", color=0x0984e3)
            view = disnake.ui.View()

            class CoinSelect(disnake.ui.Select):
                def __init__(self):
                    options = [
                        disnake.SelectOption(label="LTC", value="LTC"),
                        disnake.SelectOption(label="BNB", value="BNB"),
                        disnake.SelectOption(label="USDT", value="USDT"),
                        disnake.SelectOption(label="TRX", value="TRX"),
                        disnake.SelectOption(label="DOGE", value="DOGE"),
                        disnake.SelectOption(label="SOLANA", value="SOLANA")
                    ]
                    super().__init__(placeholder="코인을 선택하세요", min_values=1, max_values=1, options=options, custom_id="buy_coin_select")
                async def callback(self, select_inter):
                    coin = select_inter.values[0]
                    addr = get_coin_address(select_inter.author.id, coin)
                    embed2 = disnake.Embed(title=f"{coin} 매입", color=0x00b894)
                    if addr:
                        embed2.add_field(name="등록된 주소", value=f"`{addr}`", inline=False)
                    else:
                        embed2.add_field(name="등록된 주소 없음", value="먼저 /코인주소설정 으로 주소를 등록해주세요.", inline=False)

                    view2 = disnake.ui.View()
                    tx_btn = disnake.ui.Button(label="TXID 전송", style=disnake.ButtonStyle.gray, custom_id=f"open_tx_modal_{coin}")
                    view2.add_item(tx_btn)
                    bank_row = get_latest_bank(select_inter.author.id)
                    if bank_row:
                        embed2.add_field(name="입력된 계좌", value=f"{bank_row[1]} / {bank_row[2]}", inline=False)
                    await select_inter.response.send_message(embed=embed2, view=view2, ephemeral=True)

            view.add_item(CoinSelect())
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        if cid.startswith("coinaddr_modal_"):
            parts = cid.split("_")
            coin = parts[2]
            address = interaction.text_values.get("coin_address", "").strip()
            if not address:
                await interaction.response.send_message("주소를 입력해주세요.", ephemeral=True)
                return
            set_coin_address(interaction.author.id, coin, address)
            await interaction.response.send_message(f"{coin} 주소가 저장되었습니다:\n`{address}`", ephemeral=True)
            return

        if cid.startswith("txid_modal_"):
            parts = cid.split("_")
            coin = parts[2]
            txid = interaction.text_values.get("txid_value", "").strip()
            if not txid:
                await interaction.response.send_message("TXID를 입력해주세요.", ephemeral=True)
                return
            address = get_coin_address(interaction.author.id, coin)
            bank_row = get_latest_bank(interaction.author.id)
            bank_id = bank_row[0] if bank_row else None
            rec_id = save_purchase_record(interaction.author.id, bank_id, coin, address, txid, 0.0, 'KRW', status='pending')

            # 관리자 채널 알림 (가능하면)
            try:
                admin_ch = bot.get_channel(CHANNEL_CHARGE_LOG) or await bot.fetch_channel(CHANNEL_CHARGE_LOG)
                if admin_ch:
                    admin_embed = disnake.Embed(title="매입 TXID 접수", color=0xffba08)
                    admin_embed.add_field(name="사용자", value=f"{interaction.author} ({interaction.author.id})", inline=False)
                    admin_embed.add_field(name="코인", value=coin, inline=True)
                    admin_embed.add_field(name="주소", value=f"`{address}`" if address else "미등록", inline=True)
                    admin_embed.add_field(name="TXID", value=f"`{txid}`", inline=False)
                    admin_embed.add_field(name="DB ID", value=str(rec_id), inline=True)
                    admin_embed.set_footer(text=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    await admin_ch.send(embed=admin_embed)
            except Exception:
                logger.exception("관리자 알림 전송 실패")

            await interaction.response.send_message("TXID가 접수되었습니다. 운영진 확인 후 처리됩니다.", ephemeral=True)
            return

    except Exception as e:
        logger.exception(f"on_modal_submit 오류: {e}")
        try:
            await interaction.response.send_message("처리 중 오류가 발생했습니다.", ephemeral=True)
        except:
            pass

# ===== 봇 시작 =====
if __name__ == "__main__":
    bot.run(TOKEN)
