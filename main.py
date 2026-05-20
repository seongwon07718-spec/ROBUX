from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
import urllib.parse
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from dotenv import load_dotenv
import discord

# ──────────────────────────────────────────────────────────────────────────────
# 로깅
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 환경 변수
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

BLOФIN_API_KEY    = os.getenv("BLOФIN_API_KEY", "")
BLOФIN_SECRET_KEY = os.getenv("BLOФIN_SECRET_KEY", "")
BLOФIN_PASSPHRASE = os.getenv("BLOФIN_PASSPHRASE", "")
BLOФIN_BASE_URL   = "https://openapi.blofin.com"

# ──────────────────────────────────────────────────────────────────────────────
# 수수료 설정
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_SERVICE_FEE_RATE: float = 0.05
_fee_lock = asyncio.Lock()
_SERVICE_FEE_RATE: float = _DEFAULT_SERVICE_FEE_RATE


def set_service_fee_rate(rate: float) -> bool:
    global _SERVICE_FEE_RATE
    if not isinstance(rate, (int, float)) or not (0 <= rate <= 0.5):
        return False
    _SERVICE_FEE_RATE = float(rate)
    return True


def get_service_fee_rate() -> float:
    return _SERVICE_FEE_RATE


# ──────────────────────────────────────────────────────────────────────────────
# Bloфin API 서명 유틸
# ──────────────────────────────────────────────────────────────────────────────

def _bloфin_sign(
    timestamp: str,
    method: str,
    request_path: str,
    body: str = "",
) -> str:
    """HMAC-SHA256 서명 생성"""
    message = timestamp + method.upper() + request_path + (body or "")
    return hmac.new(
        BLOФIN_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _bloфin_headers(method: str, path: str, body: str = "") -> dict:
    ts = str(int(time.time() * 1000))
    return {
        "ACCESS-KEY":        BLOФIN_API_KEY,
        "ACCESS-SIGN":       _bloфin_sign(ts, method, path, body),
        "ACCESS-TIMESTAMP":  ts,
        "ACCESS-PASSPHRASE": BLOФIN_PASSPHRASE,
        "Content-Type":      "application/json",
    }


def _bloфin_get(path: str, params: Optional[dict] = None) -> dict:
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""
    full_path = path + qs
    url = BLOФIN_BASE_URL + full_path
    headers = _bloфin_headers("GET", full_path)
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _bloфin_post(path: str, payload: dict) -> dict:
    body = json.dumps(payload, separators=(",", ":"))
    url  = BLOФIN_BASE_URL + path
    headers = _bloфin_headers("POST", path, body)
    resp = requests.post(url, headers=headers, data=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ──────────────────────────────────────────────────────────────────────────────
# Bloфin 잔액 조회
# ──────────────────────────────────────────────────────────────────────────────

def get_bloфin_balance(currency: str = "USDT") -> float:
    """Bloфin 펀딩 계좌 잔액"""
    try:
        data = _bloфin_get("/api/v1/asset/balances", {"currency": currency.upper()})
        items = data.get("data") or []
        for item in items:
            if item.get("currency", "").upper() == currency.upper():
                return float(item.get("available", 0))
        return 0.0
    except Exception as e:
        log.warning("Bloфin 잔액 조회 실패 [%s]: %s", currency, e)
        return 0.0


def get_all_balances() -> dict:
    coins = ["USDT", "BTC", "ETH", "LTC", "TRX", "BNB", "SOL"]
    return {c: get_bloфin_balance(c) for c in coins}


# ──────────────────────────────────────────────────────────────────────────────
# Bloфin 출금 (송금)
# ──────────────────────────────────────────────────────────────────────────────

# Bloфin chain 코드 매핑
_CHAIN_MAP: dict[tuple[str, str], str] = {
    ("USDT", "BEP20"):  "BSC",
    ("USDT", "TRC20"):  "TRC20",
    ("USDT", "ERC20"):  "ERC20",
    ("TRX",  "TRC20"):  "TRC20",
    ("LTC",  "LTC"):    "LTC",
    ("BNB",  "BEP20"):  "BSC",
    ("SOL",  "SOL"):    "SOL",
    ("ETH",  "ERC20"):  "ERC20",
    ("BTC",  "BTC"):    "Bitcoin",
}


def _get_chain(coin: str, network: str) -> str:
    key = (coin.upper(), network.upper())
    chain = _CHAIN_MAP.get(key)
    if not chain:
        raise ValueError(f"지원하지 않는 코인/네트워크 조합: {coin}/{network}")
    return chain


def bloфin_withdraw(
    coin: str,
    amount: float,
    to_address: str,
    network: str,
) -> dict:
    """
    Bloфin 출금 API 호출
    반환값: {"withdrawal_id", "coin", "amount", "to_address", "network", "time"}
    """
    chain = _get_chain(coin, network)

    # 금액을 안전하게 문자열 변환 (부동소수점 오차 방지)
    try:
        amount_str = str(Decimal(str(amount)).normalize())
    except InvalidOperation:
        raise ValueError(f"유효하지 않은 금액: {amount}")

    payload = {
        "currency":    coin.upper(),
        "amount":      amount_str,
        "toAddress":   to_address,
        "chain":       chain,
        "walletType":  "funding",  # 펀딩 계좌에서 출금
    }

    data = _bloфin_post("/api/v1/asset/withdrawal", payload)
    code = data.get("code", "")
    if str(code) != "0":
        msg = data.get("msg", "알 수 없는 오류")
        raise RuntimeError(f"Bloфin 출금 실패 (code={code}): {msg}")

    result_data = data.get("data") or {}
    return {
        "withdrawal_id": result_data.get("withdrawalId", "N/A"),
        "coin":          coin.upper(),
        "amount":        amount_str,
        "to_address":    to_address,
        "network":       network,
        "chain":         chain,
        "time":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_bloфin_withdrawal_status(withdrawal_id: str) -> dict:
    """출금 상태 조회"""
    try:
        data = _bloфin_get(
            "/api/v1/asset/withdrawal-history",
            {"withdrawalId": withdrawal_id},
        )
        items = data.get("data") or []
        return items[0] if items else {}
    except Exception as e:
        log.warning("출금 상태 조회 실패 [%s]: %s", withdrawal_id, e)
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# 환율 / 시세
# ──────────────────────────────────────────────────────────────────────────────

def get_exchange_rate() -> float:
    """USD → KRW 환율"""
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD", timeout=10
        )
        r.raise_for_status()
        rate = r.json().get("rates", {}).get("KRW")
        if rate and rate > 0:
            return float(rate)
    except Exception:
        pass
    return 1350.0


def get_kimchi_premium() -> float:
    try:
        upbit = requests.get(
            "https://api.upbit.com/v1/ticker?markets=KRW-BTC", timeout=10
        ).json()
        upbit_price = float(upbit[0]["trade_price"])
        binance = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10
        ).json()
        binance_krw = float(binance["price"]) * get_exchange_rate()
        return round(((upbit_price - binance_krw) / binance_krw) * 100, 2)
    except Exception:
        return 0.0


def get_coin_price(symbol: str) -> float:
    """USD 기준 가격"""
    symbol = symbol.upper()
    if symbol == "USDT":
        return 1.0

    upbit_map = {"LTC": "KRW-LTC", "BNB": "KRW-BNB", "TRX": "KRW-TRX"}
    if symbol in upbit_map:
        try:
            r = requests.get(
                f"https://api.upbit.com/v1/ticker?markets={upbit_map[symbol]}",
                timeout=10,
            ).json()
            krw = float(r[0]["trade_price"])
            return krw / get_exchange_rate()
        except Exception:
            pass

    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT",
            timeout=10,
        ).json()
        return float(r["price"])
    except Exception:
        return 0.0


def coin_to_usdt(coin_amount: float, coin: str) -> float:
    price = get_coin_price(coin.upper())
    return coin_amount * price if price > 0 else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 최소 출금 수량
# ──────────────────────────────────────────────────────────────────────────────

MINIMUM_COIN_AMOUNTS: dict[str, float] = {
    "USDT": 10.0,
    "TRX":  10.0,
    "LTC":  0.015,
    "BNB":  0.008,
    "SOL":  0.1,
    "ETH":  0.003,
    "BTC":  0.00005,
}


def get_minimum_amounts_krw() -> dict:
    krw_rate = get_exchange_rate()
    kimchi   = get_kimchi_premium()
    actual   = krw_rate * (1 + kimchi / 100)
    return {
        coin: int(amt * get_coin_price(coin) * actual)
        for coin, amt in MINIMUM_COIN_AMOUNTS.items()
    }


def get_minimum_amounts_usd() -> dict:
    return {
        coin: round(amt * get_coin_price(coin), 4)
        for coin, amt in MINIMUM_COIN_AMOUNTS.items()
    }


# ──────────────────────────────────────────────────────────────────────────────
# DB 헬퍼 (취약점 수정)
# ──────────────────────────────────────────────────────────────────────────────

_DB_VERIFY = "DB/verify_user.db"
_DB_HIST   = "DB/history.db"


def get_verified_user(user_id: int) -> Optional[tuple]:
    try:
        conn = sqlite3.connect(_DB_VERIFY, timeout=5)
        cur  = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row  = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        log.warning("get_verified_user 오류 [%s]: %s", user_id, e)
        return None


def subtract_balance(user_id: int, amount: int) -> bool:
    """
    잔액 차감 - 단일 UPDATE WHERE 로 TOCTOU 취약점 방지.
    amount가 음수/0이면 거부.
    """
    if not isinstance(amount, int) or amount <= 0:
        return False
    conn = None
    try:
        conn = sqlite3.connect(_DB_VERIFY, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET now_amount = now_amount - ? "
            "WHERE user_id = ? AND now_amount >= ?",
            (amount, user_id, amount),
        )
        conn.commit()
        return cur.rowcount == 1
    except Exception as e:
        log.error("subtract_balance 오류 [%s]: %s", user_id, e)
        if conn:
            try: conn.rollback()
            except Exception: pass
        return False
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def refund_balance(user_id: int, amount: int) -> bool:
    """환불 - amount 유효성 검사 포함"""
    if not isinstance(amount, int) or amount <= 0:
        return False
    conn = None
    try:
        conn = sqlite3.connect(_DB_VERIFY, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "UPDATE users SET now_amount = now_amount + ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("refund_balance 오류 [%s]: %s", user_id, e)
        if conn:
            try: conn.rollback()
            except Exception: pass
        return False
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def add_transaction_history(user_id: int, amount: int, tx_type: str) -> None:
    conn = None
    try:
        conn = sqlite3.connect(_DB_HIST, timeout=5)
        conn.execute(
            "INSERT INTO transaction_history (user_id, amount, type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, amount, tx_type, datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        log.warning("add_transaction_history 오류 [%s]: %s", user_id, e)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def get_user_tier_and_fee(user_id: int) -> tuple[str, float, float]:
    """(tier, service_fee_rate, purchase_bonus_rate)"""
    try:
        conn  = sqlite3.connect(_DB_VERIFY, timeout=5)
        cur   = conn.cursor()
        cur.execute("SELECT Total_amount FROM users WHERE user_id = ?", (user_id,))
        row   = cur.fetchone()
        conn.close()
        total = int(row[0] or 0) if row else 0
        if total >= 10_000_000:
            return ("VIP", 0.03, 0.01)
        return ("BUYER", 0.05, 0.0)
    except Exception:
        return ("BUYER", 0.05, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# 수수료 계산
# ──────────────────────────────────────────────────────────────────────────────

def calculate_fees(
    raw_amount: float,
    coin: str,
    network: str,
    user_id: int,
    currency_mode: str = "KRW",
) -> dict:
    """
    currency_mode: 'KRW' | 'USD' | 'COIN'
    반환값에 coin_to_send(Bloфin에서 출금할 코인 수량) 포함
    """
    krw_rate    = get_exchange_rate()
    kimchi      = get_kimchi_premium()
    actual_rate = krw_rate * (1 + kimchi / 100)
    coin_price  = get_coin_price(coin.upper())

    _, svc_fee_rate, _ = get_user_tier_and_fee(user_id)

    # 금액을 USDT로 변환
    if currency_mode == "KRW":
        gross_usdt = raw_amount / actual_rate if actual_rate > 0 else 0.0
    elif currency_mode == "USD":
        gross_usdt = float(raw_amount)
    else:  # COIN
        gross_usdt = coin_to_usdt(raw_amount, coin)

    service_fee_usdt     = gross_usdt * svc_fee_rate
    net_usdt             = gross_usdt - service_fee_usdt
    coin_to_send         = (net_usdt / coin_price) if coin_price > 0 else 0.0

    gross_krw       = gross_usdt * actual_rate
    service_fee_krw = service_fee_usdt * actual_rate
    net_krw         = net_usdt * actual_rate

    return {
        "gross_usdt":           gross_usdt,
        "net_usdt":             net_usdt,
        "coin_to_send":         coin_to_send,
        "service_fee_usdt":     service_fee_usdt,
        "service_fee_krw":      service_fee_krw,
        "gross_krw":            gross_krw,
        "net_krw":              net_krw,
        "krw_rate":             krw_rate,
        "kimchi_premium":       kimchi,
        "actual_krw_rate":      actual_rate,
        "coin_price":           coin_price,
        "fee_rate":             svc_fee_rate,
        # 하위 호환 필드
        "expected_coin_amount": coin_to_send,
        "actual_send_amount":   coin_to_send,
        "actual_send_krw":      net_krw,
        "total_fee_krw":        service_fee_krw,
    }


def _preview_fees(
    amount: float,
    coin: str,
    network: str,
    currency_mode: str,
) -> dict:
    """user_id 없이 기본 수수료로 미리보기"""
    krw_rate    = get_exchange_rate()
    kimchi      = get_kimchi_premium()
    actual_rate = krw_rate * (1 + kimchi / 100)
    coin_price  = get_coin_price(coin.upper())
    fee_rate    = _SERVICE_FEE_RATE

    if currency_mode == "KRW":
        gross_usdt = amount / actual_rate if actual_rate > 0 else 0.0
    elif currency_mode == "USD":
        gross_usdt = amount
    else:
        gross_usdt = coin_to_usdt(amount, coin)

    net_usdt     = gross_usdt * (1 - fee_rate)
    coin_to_send = (net_usdt / coin_price) if coin_price > 0 else 0.0

    return {
        "gross_usdt":           gross_usdt,
        "net_usdt":             net_usdt,
        "coin_to_send":         coin_to_send,
        "expected_coin_amount": coin_to_send,
        "fee_rate":             fee_rate,
        "kimchi_premium":       kimchi,
        "actual_krw_rate":      actual_rate,
        "coin_price":           coin_price,
    }


# ──────────────────────────────────────────────────────────────────────────────
# pending_transactions (경쟁 조건 방지)
# ──────────────────────────────────────────────────────────────────────────────

_pending_lock = asyncio.Lock()
_pending_transactions: dict[int, dict] = {}


async def _set_pending(user_id: int, data: dict) -> None:
    async with _pending_lock:
        _pending_transactions[user_id] = data


async def _get_pending(user_id: int) -> Optional[dict]:
    async with _pending_lock:
        return _pending_transactions.get(user_id)


async def _pop_pending(user_id: int) -> Optional[dict]:
    async with _pending_lock:
        return _pending_transactions.pop(user_id, None)


# ──────────────────────────────────────────────────────────────────────────────
# 코인 / 네트워크 정보
# ──────────────────────────────────────────────────────────────────────────────

SUPPORTED_COINS = [
    discord.SelectOption(label="USDT",  description="Tether (BEP20 / TRC20 / ERC20)", value="USDT"),
    discord.SelectOption(label="TRX",   description="Tron",                            value="TRX"),
    discord.SelectOption(label="LTC",   description="Litecoin",                        value="LTC"),
    discord.SelectOption(label="BNB",   description="Binance Coin (BSC)",              value="BNB"),
    discord.SelectOption(label="SOL",   description="Solana",                          value="SOL"),
    discord.SelectOption(label="ETH",   description="Ethereum",                        value="ETH"),
    discord.SelectOption(label="BTC",   description="Bitcoin",                         value="BTC"),
]

COIN_NETWORKS: dict[str, list[str]] = {
    "USDT": ["BEP20", "TRC20", "ERC20"],
    "TRX":  ["TRC20"],
    "LTC":  ["LTC"],
    "BNB":  ["BEP20"],
    "SOL":  ["SOL"],
    "ETH":  ["ERC20"],
    "BTC":  ["BTC"],
}


# ──────────────────────────────────────────────────────────────────────────────
# Discord UI 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_error_view(msg: str) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=180)
    view.add_item(
        discord.ui.Container(
            discord.ui.TextDisplay(f"## 오류\n{msg}"),
            accent_color=0xCF222E,
        )
    )
    return view


async def _edit_layout(
    interaction: discord.Interaction,
    view: discord.ui.LayoutView,
) -> None:
    await interaction.edit_original_response(
        content=None, embed=None, attachments=[], view=view
    )


# ──────────────────────────────────────────────────────────────────────────────
# UI 컴포넌트
# ──────────────────────────────────────────────────────────────────────────────

class CoinSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="코인을 선택하세요",
            custom_id="coin_select",
            options=SUPPORTED_COINS,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not get_verified_user(interaction.user.id):
            await _edit_layout(interaction, _make_error_view("인증되지 않은 사용자입니다."))
            return
        await _edit_layout(interaction, SendLayout(coin=self.values[0]))


class NetworkSelect(discord.ui.Select):
    def __init__(self, coin: str, disabled: bool = False) -> None:
        networks = COIN_NETWORKS.get(coin.upper(), ["BEP20"])
        options  = [discord.SelectOption(label=n, value=n) for n in networks]
        super().__init__(
            placeholder="네트워크를 선택하세요",
            custom_id=f"network_select_{coin}",
            options=options,
            disabled=disabled,
            row=1,
        )
        self.coin = coin

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SendLayout = self.view  # type: ignore
        await interaction.response.defer(ephemeral=True)
        await _edit_layout(
            interaction,
            SendLayout(
                coin=view.coin,
                network=self.values[0],
                currency_mode=view.currency_mode,
                amount_str=view.amount_str,
                address=view.address,
            ),
        )


class CurrencyButton(discord.ui.Button):
    def __init__(
        self,
        label: str,
        mode: str,
        selected: bool,
        disabled: bool = False,
        row: int = 2,
    ) -> None:
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary if selected else discord.ButtonStyle.secondary,
            custom_id=f"currency_{mode}",
            disabled=disabled,
            row=row,
        )
        self.mode = mode

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SendLayout = self.view  # type: ignore
        await interaction.response.defer(ephemeral=True)
        await _edit_layout(
            interaction,
            SendLayout(
                coin=view.coin,
                network=view.network,
                currency_mode=self.mode,
                amount_str=view.amount_str,
                address=view.address,
            ),
        )


class AmountInputButton(discord.ui.Button):
    def __init__(self, current: str, coin: str, disabled: bool = False) -> None:
        label = f"금액: {current}" if current else "금액 입력"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id="amount_input_btn",
            disabled=disabled,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SendLayout = self.view  # type: ignore
        await interaction.response.send_modal(
            AmountInputModal(
                view.coin, view.network, view.currency_mode, view.address
            )
        )


class AddressInputButton(discord.ui.Button):
    def __init__(self, current: str, disabled: bool = False) -> None:
        label = f"주소: {current[:10]}..." if current else "받을 주소 입력"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id="address_input_btn",
            disabled=disabled,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SendLayout = self.view  # type: ignore
        await interaction.response.send_modal(
            AddressInputModal(
                view.coin, view.network, view.currency_mode, view.amount_str
            )
        )


class SendExecuteButton(discord.ui.Button):
    def __init__(self, disabled: bool = True) -> None:
        super().__init__(
            label="송금하기",
            style=discord.ButtonStyle.success,
            custom_id="send_execute_btn",
            disabled=disabled,
            row=4,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SendLayout = self.view  # type: ignore
        await handle_send_execute(interaction, view)


class CancelButton(discord.ui.Button):
    def __init__(self, row: int = 4) -> None:
        super().__init__(
            label="취소",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_btn",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await _pop_pending(interaction.user.id)
        await interaction.response.defer(ephemeral=True)
        view = discord.ui.LayoutView(timeout=1)
        view.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## 취소됨\n송금이 취소되었습니다."),
                accent_color=0x6E7681,
            )
        )
        await _edit_layout(interaction, view)


# ──────────────────────────────────────────────────────────────────────────────
# 송금 메인 레이아웃
# ──────────────────────────────────────────────────────────────────────────────

class SendLayout(discord.ui.LayoutView):
    def __init__(
        self,
        coin: str = "",
        network: str = "",
        currency_mode: str = "KRW",
        amount_str: str = "",
        address: str = "",
    ) -> None:
        super().__init__(timeout=300)
        self.coin          = coin
        self.network       = network or (COIN_NETWORKS.get(coin, [""])[0] if coin else "")
        self.currency_mode = currency_mode
        self.amount_str    = amount_str
        self.address       = address

        no_coin  = not coin
        can_send = bool(coin and amount_str and address)

        # Row 0 — 코인 선택
        coin_row = discord.ui.ActionRow(CoinSelect())

        # Row 1 — 네트워크 선택
        net_row = discord.ui.ActionRow(
            NetworkSelect(coin or "USDT", disabled=no_coin)
        )

        # Row 2 — 통화 단위
        cur_row = discord.ui.ActionRow(
            CurrencyButton("KRW",  "KRW",  currency_mode == "KRW",  disabled=no_coin, row=2),
            CurrencyButton("USD",  "USD",  currency_mode == "USD",  disabled=no_coin, row=2),
            CurrencyButton("COIN", "COIN", currency_mode == "COIN", disabled=no_coin, row=2),
        )

        # Row 3 — 금액 / 주소 입력
        input_row = discord.ui.ActionRow(
            AmountInputButton(amount_str, coin, disabled=no_coin),
            AddressInputButton(address,         disabled=no_coin),
        )

        # Row 4 — 실행 / 취소
        exec_row = discord.ui.ActionRow(
            SendExecuteButton(disabled=not can_send),
            CancelButton(row=4),
        )

        # 텍스트 패널
        lines = ["## 송금"]
        if coin:
            lines.append(f"코인    `{coin}`")
            if self.network:
                lines.append(f"네트워크  `{self.network}`")
        else:
            lines.append("-# 코인을 먼저 선택하세요.")

        if coin and amount_str:
            try:
                fees = _preview_fees(
                    float(amount_str.replace(",", "")),
                    coin, self.network, currency_mode,
                )
                lines.append(
                    f"\n예상 수령    `{fees['coin_to_send']:.6f} {coin}`\n"
                    f"수수료       `{fees['fee_rate']*100:.1f}%`"
                )
            except Exception:
                pass

        if coin and address:
            lines.append(f"수신 주소  `{address[:14]}...{address[-6:]}`")

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("\n".join(lines)),
                coin_row,
                discord.ui.Separator(),
                discord.ui.TextDisplay("-# 네트워크"),
                net_row,
                discord.ui.Separator(),
                discord.ui.TextDisplay("-# 통화 단위"),
                cur_row,
                discord.ui.Separator(),
                input_row,
                discord.ui.Separator(),
                exec_row,
                accent_color=0x1C2128,
            )
        )


# ──────────────────────────────────────────────────────────────────────────────
# 모달
# ──────────────────────────────────────────────────────────────────────────────

class AmountInputModal(discord.ui.Modal):
    def __init__(
        self,
        coin: str,
        network: str,
        currency_mode: str,
        address: str,
    ) -> None:
        self.coin          = coin
        self.network       = network
        self.currency_mode = currency_mode
        self.address       = address

        unit_label = {
            "KRW":  "원화 금액 (KRW)",
            "USD":  "달러 금액 (USD)",
            "COIN": f"코인 수량 ({coin})",
        }
        placeholder = {
            "KRW":  "예: 100000",
            "USD":  "예: 75.00",
            "COIN": "예: 0.05",
        }
        super().__init__(
            title=f"{coin} 금액 입력",
            custom_id=f"amount_modal_{coin}_{network}",
            timeout=180,
        )
        self.amount_input = discord.ui.TextInput(
            label=unit_label.get(currency_mode, "금액"),
            custom_id="amount_input",
            placeholder=placeholder.get(currency_mode, "금액 입력"),
            style=discord.TextStyle.short,
            min_length=1,
            max_length=20,
            required=True,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await _edit_layout(
            interaction,
            SendLayout(
                coin=self.coin,
                network=self.network,
                currency_mode=self.currency_mode,
                amount_str=self.amount_input.value.strip(),
                address=self.address,
            ),
        )


class AddressInputModal(discord.ui.Modal):
    def __init__(
        self,
        coin: str,
        network: str,
        currency_mode: str,
        amount_str: str,
    ) -> None:
        self.coin          = coin
        self.network       = network
        self.currency_mode = currency_mode
        self.amount_str    = amount_str

        super().__init__(
            title="수신 주소 입력",
            custom_id=f"address_modal_{coin}",
            timeout=180,
        )
        self.address_input = discord.ui.TextInput(
            label="받을 지갑 주소",
            custom_id="address_input",
            placeholder="주소를 정확히 입력하세요. 오입력 시 자산이 영구 손실됩니다.",
            style=discord.TextStyle.short,
            min_length=10,
            max_length=200,
            required=True,
        )
        self.add_item(self.address_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await _edit_layout(
            interaction,
            SendLayout(
                coin=self.coin,
                network=self.network,
                currency_mode=self.currency_mode,
                amount_str=self.amount_str,
                address=self.address_input.value.strip(),
            ),
        )


# ──────────────────────────────────────────────────────────────────────────────
# 송금 실행 핸들러
# ──────────────────────────────────────────────────────────────────────────────

async def handle_send_execute(
    interaction: discord.Interaction,
    view: SendLayout,
) -> None:
    await interaction.response.defer(ephemeral=True)

    user_data = get_verified_user(interaction.user.id)
    if not user_data:
        await _edit_layout(interaction, _make_error_view("인증되지 않은 사용자입니다."))
        return

    coin          = view.coin.upper()
    network       = view.network.upper()
    address       = view.address.strip()
    amount_str    = view.amount_str.strip()
    currency_mode = view.currency_mode

    # 금액 파싱
    try:
        raw_amount = float(amount_str.replace(",", ""))
        if raw_amount <= 0:
            raise ValueError
    except ValueError:
        await _edit_layout(interaction, _make_error_view("올바른 금액을 입력해주세요."))
        return

    # 수수료 계산
    fees      = calculate_fees(raw_amount, coin, network, interaction.user.id, currency_mode)
    gross_krw = fees["gross_krw"]

    # 최소 금액 검사
    min_krw = get_minimum_amounts_krw().get(coin, 10_000)
    if gross_krw < min_krw:
        await _edit_layout(
            interaction,
            _make_error_view(f"최소 송금 금액은 {min_krw:,}원입니다."),
        )
        return

    # 잔액 검사 (DB 직접 조회 — 실제 차감은 confirm 시)
    current_balance = int(user_data[6]) if len(user_data) > 6 else 0
    if current_balance < int(gross_krw):
        await _edit_layout(
            interaction,
            _make_error_view(
                f"잔액 부족\n보유: {current_balance:,}원  /  필요: {int(gross_krw):,}원"
            ),
        )
        return

    # pending 저장
    await _set_pending(interaction.user.id, {
        "coin":          coin,
        "network":       network,
        "address":       address,
        "krw_amount":    int(gross_krw),
        "coin_to_send":  fees["coin_to_send"],
        "currency_mode": currency_mode,
        "raw_amount":    raw_amount,
        **fees,
    })

    await _edit_layout(
        interaction,
        ConfirmLayout(coin, network, address, int(gross_krw), fees),
    )


# ──────────────────────────────────────────────────────────────────────────────
# 확인 / 처리 중 / 결과 레이아웃
# ──────────────────────────────────────────────────────────────────────────────

class ConfirmSendButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="최종 송금",
            style=discord.ButtonStyle.danger,
            custom_id="confirm_send_btn",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await handle_confirmed_send(interaction)


class ConfirmLayout(discord.ui.LayoutView):
    def __init__(
        self,
        coin: str,
        network: str,
        address: str,
        krw_amount: int,
        fees: dict,
    ) -> None:
        super().__init__(timeout=180)
        row = discord.ui.ActionRow(ConfirmSendButton(), CancelButton(row=0))
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## 송금 확인  —  {coin}"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"예상 수령\n"
                    f"```{fees['coin_to_send']:.6f} {coin}```"
                ),
                discord.ui.TextDisplay(
                    f"차감 금액\n"
                    f"```{krw_amount:,} 원```"
                ),
                discord.ui.TextDisplay(
                    f"수수료\n"
                    f"```{fees['fee_rate']*100:.1f}%   ({int(fees['service_fee_krw']):,} 원)```"
                ),
                discord.ui.TextDisplay(
                    f"환율 정보\n"
                    f"```기본환율       {fees['krw_rate']:.0f} 원\n"
                    f"김치프리미엄   {fees['kimchi_premium']:+.2f}%\n"
                    f"적용환율       {fees['actual_krw_rate']:.0f} 원```"
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"수신 주소\n```{address}```"
                ),
                discord.ui.TextDisplay(
                    f"네트워크\n```{network}```"
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    "주소를 다시 확인하세요. 잘못된 주소로 송금된 자산은 복구할 수 없습니다."
                ),
                discord.ui.Separator(),
                row,
                accent_color=0xD29922,
            )
        )


class ProcessingLayout(discord.ui.LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout=180)
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## 처리 중"),
                discord.ui.TextDisplay(
                    "Bloфin을 통해 출금 요청을 전송하고 있습니다. 잠시만 기다려주세요."
                ),
                accent_color=0xD29922,
            )
        )


class SuccessLayout(discord.ui.LayoutView):
    def __init__(
        self,
        coin: str,
        fees: dict,
        krw_amount: int,
        result: dict,
    ) -> None:
        super().__init__(timeout=180)
        wid = result.get("withdrawal_id", "N/A")
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## 송금 완료  —  {coin}"),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"예상 수령\n"
                    f"```{fees['coin_to_send']:.6f} {coin}```"
                ),
                discord.ui.TextDisplay(
                    f"총 차감\n```{krw_amount:,} 원```"
                ),
                discord.ui.TextDisplay(
                    f"환율\n"
                    f"```기본환율       {int(fees['krw_rate']):,} 원\n"
                    f"김치프리미엄   {fees['kimchi_premium']:+.2f}%\n"
                    f"적용환율       {int(fees['actual_krw_rate']):,} 원```"
                ),
                discord.ui.TextDisplay(
                    f"수수료\n```{int(fees['service_fee_krw']):,} 원```"
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(
                    f"Bloфin 출금 ID\n```{wid}```"
                ),
                discord.ui.TextDisplay(
                    f"수신 주소\n```{result.get('to_address', 'N/A')}```"
                ),
                discord.ui.TextDisplay(
                    f"네트워크 / 체인\n```{result.get('network', 'N/A')}  /  {result.get('chain', 'N/A')}```"
                ),
                discord.ui.TextDisplay(
                    f"처리 시각\n```{result.get('time', 'N/A')}```"
                ),
                accent_color=0x1A7F37,
            )
        )


class FailLayout(discord.ui.LayoutView):
    def __init__(
        self,
        coin: str,
        network: str,
        address: str,
        krw_amount: int,
        error_msg: str,
    ) -> None:
        super().__init__(timeout=180)
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## 송금 실패  —  환불 처리됨"),
                discord.ui.TextDisplay(
                    f"오류로 인해 **{krw_amount:,}원** 이 환불되었습니다."
                ),
                discord.ui.Separator(),
                discord.ui.TextDisplay(f"오류\n```{error_msg}```"),
                discord.ui.TextDisplay(
                    f"요청 정보\n"
                    f"```코인       {coin}\n"
                    f"네트워크   {network}\n"
                    f"주소       {address[:10]}...{address[-6:]}```"
                ),
                accent_color=0xCF222E,
            )
        )


# ──────────────────────────────────────────────────────────────────────────────
# 최종 송금 확인 핸들러
# ──────────────────────────────────────────────────────────────────────────────

async def handle_confirmed_send(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)

    user_data = get_verified_user(interaction.user.id)
    if not user_data:
        await _edit_layout(interaction, _make_error_view("인증되지 않은 사용자입니다."))
        return

    tx_data = await _get_pending(interaction.user.id)
    if not tx_data:
        await _edit_layout(
            interaction,
            _make_error_view("송금 정보를 찾을 수 없습니다. 처음부터 다시 시도해주세요."),
        )
        return

    coin        = tx_data["coin"]
    network     = tx_data["network"]
    address     = tx_data["address"]
    krw_amount  = tx_data["krw_amount"]
    coin_amount = tx_data["coin_to_send"]

    # 단일 UPDATE WHERE 로 잔액 차감 (TOCTOU 방지)
    if not subtract_balance(interaction.user.id, krw_amount):
        await _edit_layout(
            interaction,
            _make_error_view("잔액 부족으로 처리할 수 없습니다."),
        )
        return

    await _edit_layout(interaction, ProcessingLayout())

    # Bloфin 출금 요청 (blocking → executor)
    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: bloфin_withdraw(coin, coin_amount, address, network),
        )
        success    = True
        error_msg  = ""
    except Exception as e:
        success    = False
        error_msg  = str(e)
        result     = {}

    if success:
        add_transaction_history(interaction.user.id, krw_amount, "송금")
        await _edit_layout(
            interaction,
            SuccessLayout(coin, tx_data, krw_amount, result),
        )

        # 관리자 로그
        try:
            from bot import CHANNEL_ADMIN_LOG, bot as _bot
            admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            if admin_ch:
                e = discord.Embed(title="코인 송금 완료 (Bloфin)", color=0x1A7F37)
                e.add_field(name="고객",          value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                e.add_field(name="총 차감",        value=f"{krw_amount:,}원",                    inline=True)
                e.add_field(name="출금량",         value=f"{coin_amount:.6f} {coin}",             inline=True)
                e.add_field(name="네트워크",       value=f"{coin} / {network}",                  inline=True)
                e.add_field(name="출금 ID",        value=result.get("withdrawal_id", "N/A"),     inline=False)
                e.add_field(name="수신 주소",      value=address,                                inline=False)
                await admin_ch.send(embed=e)
        except Exception:
            pass

    else:
        # 실패 시 환불
        if not refund_balance(interaction.user.id, krw_amount):
            log.error(
                "환불 실패! user_id=%s, amount=%s. 수동 처리 필요.",
                interaction.user.id, krw_amount,
            )
        add_transaction_history(interaction.user.id, krw_amount, "환불")
        await _edit_layout(
            interaction,
            FailLayout(coin, network, address, krw_amount, error_msg),
        )

        # 관리자 로그
        try:
            from bot import CHANNEL_ADMIN_LOG, bot as _bot
            admin_ch = _bot.get_channel(CHANNEL_ADMIN_LOG)
            if admin_ch:
                e = discord.Embed(title="코인 송금 실패 (Bloфin)", color=0xCF222E)
                e.add_field(name="고객",    value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                e.add_field(name="환불액",  value=f"{krw_amount:,}원",       inline=True)
                e.add_field(name="코인",    value=f"{coin} / {network}",     inline=True)
                e.add_field(name="주소",    value=address,                   inline=False)
                e.add_field(name="오류",    value=f"```{error_msg}```",      inline=False)
                await admin_ch.send(embed=e)
        except Exception:
            pass

    await _pop_pending(interaction.user.id)


# ──────────────────────────────────────────────────────────────────────────────
# 공개 진입점
# ──────────────────────────────────────────────────────────────────────────────

def get_coin_send_view() -> discord.ui.LayoutView:
    """슬래시 커맨드 / 버튼 핸들러에서 view=get_coin_send_view() 로 호출하세요."""
    return SendLayout()


def get_balance(currency: str = "USDT") -> str:
    return str(get_bloфin_balance(currency.upper()))


# 하위 호환 더미 (사용처가 있을 경우)
def init_coin_selenium() -> bool:
    return True


def quit_driver() -> None:
    pass
