import asyncio
import random
import string
import sqlite3
import requests
import discord
from discord import ui

DATABASE = "database.db"

# -----------------------------------
# 🔧 유틸 함수
# -----------------------------------
def get_container_view(title: str, description: str, color: int):
    """간단한 컨테이너 뷰를 생성하는 헬퍼 함수"""
    class SimpleView(ui.LayoutView):
        async def build(self):
            con = ui.Container()
            con.accent_color = color
            con.add_item(ui.TextDisplay(f"### {title}\n-# {description}"))
            self.clear_items()
            self.add_item(con)
            return self
    return SimpleView()


# -----------------------------------
# 1️⃣ Roblox API 클래스
# -----------------------------------
class RobloxAPI:
    BASE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, cookie: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(self.BASE_HEADERS)
        if cookie:
            # '_|WARNING:-DO-NOT-SHARE...|_' 형식 전부 처리
            clean = cookie.strip()
            if "=" in clean:
                clean = clean.split("=", 1)[-1]
            self.session.cookies.set(".ROBLOSECURITY", clean, domain=".roblox.com")

    # ── CSRF ──────────────────────────────────────────────────────────────────
    def get_csrf_token(self) -> str | None:
        resp = self.session.post("https://auth.roblox.com/v2/logout")
        return resp.headers.get("x-csrf-token")

    # ── 유저 ──────────────────────────────────────────────────────────────────
    def get_user_id(self, nickname: str) -> int | None:
        resp = self.session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [nickname], "excludeBannedUsers": True},
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        return data[0].get("id") if data else None

    # ── 게임 목록 ─────────────────────────────────────────────────────────────
    def get_user_places(self, user_id: int) -> list[dict]:
        url = f"https://games.roblox.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc"
        resp = self.session.get(url)
        if resp.status_code != 200:
            return []
        games = []
        for g in resp.json().get("data", []):
            if g.get("isPublic"):
                games.append({
                    "id": g.get("id"),            # Universe ID
                    "name": g.get("name") or "이름 없는 게임",
                    "rootPlaceId": g.get("rootPlaceId"),  # Place ID
                })
        return games

    # ── 게임패스 목록 ─────────────────────────────────────────────────────────
    def get_place_gamepasses(self, universe_id: int) -> list[dict]:
        url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=100&sortOrder=Asc"
        resp = self.session.get(url)
        if resp.status_code != 200:
            return []
        # price가 None이면 판매 중단 → 제외
        return [p for p in resp.json().get("data", []) if p.get("price") is not None]

    # ── 게임패스 상품 정보 ────────────────────────────────────────────────────
    def get_gamepass_product_info(self, pass_id: int) -> dict | None:
        resp = self.session.get(
            f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info"
        )
        return resp.json() if resp.status_code == 200 else None

    # ── 게임패스 구매 ─────────────────────────────────────────────────────────
    def buy_gamepass(self, pass_id: int) -> dict:
        """
        Returns {"purchased": bool, "reason": str | None, ...}
        """
        info = self.get_gamepass_product_info(pass_id)
        if not info:
            return {"purchased": False, "reason": "상품 정보 조회 실패"}

        product_id = info.get("ProductId")
        price = info.get("PriceInRobux", 0)
        seller_id = (info.get("Creator") or {}).get("Id")

        if not product_id:
            return {"purchased": False, "reason": "ProductId 없음"}

        token = self.get_csrf_token()
        if not token:
            return {"purchased": False, "reason": "CSRF 토큰 획득 실패"}

        headers = {
            "x-csrf-token": token,
            "Content-Type": "application/json",
            "Referer": f"https://www.roblox.com/game-pass/{pass_id}",
        }
        payload = {
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedSellerId": seller_id,
        }
        resp = self.session.post(
            f"https://economy.roblox.com/v1/purchases/products/{product_id}",
            json=payload,
            headers=headers,
        )
        try:
            return resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}


# -----------------------------------
# 2️⃣ 결제 처리 로직
# -----------------------------------
def process_manual_buy(pass_id: int, user_id: str, money: int) -> dict:
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        row = cur.fetchone()

    if not row:
        return {"success": False, "message": "관리자 쿠키가 설정되지 않았습니다."}

    api = RobloxAPI(row[0])
    result = api.buy_gamepass(pass_id)

    if not result.get("purchased"):
        reason = result.get("reason") or result.get("errorMessage") or "구매 조건이 맞지 않습니다."
        return {"success": False, "message": reason}

    # 구매 성공 → DB 기록
    robux = result.get("currency", {}).get("robux", 0) or 0
    order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (money, user_id),
        )
        cur.execute(
            "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
            (order_id, user_id, money, robux),
        )
        conn.commit()

    return {"success": True, "order_id": order_id}


# -----------------------------------
# 3️⃣ UI 뷰 클래스
# -----------------------------------

# ── 최종 결제 확인 ─────────────────────────────────────────────────────────────
class FinalBuyView(ui.LayoutView):
    def __init__(self, pass_info: dict, money: int, user_id: int | str):
        super().__init__(timeout=60)
        self.pass_info = pass_info
        self.money = money
        self.user_id = str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = (
            "### <:acy2:1489883409001091142> 최종 결제 확인\n"
            f"-# - **아이템**: {self.pass_info.get('name', '알 수 없음')}\n"
            f"-# - **로벅스**: {self.pass_info.get('price', 0):,} R$\n"
            f"-# - **차감금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(text))

        btn = ui.Button(label="결제 승인", style=discord.ButtonStyle.gray, emoji="✅")
        btn.callback = self.do_buy
        con.add_item(ui.ActionRow().add_item(btn))

        self.clear_items()
        self.add_item(con)
        return self

    async def do_buy(self, it: discord.Interaction):
        # 먼저 상태 업데이트
        processing = get_container_view("⌛ 처리 중", "서버와 통신 중입니다...", 0xFEE75C)
        await it.response.edit_message(view=await processing.build())

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            process_manual_buy,
            self.pass_info["id"],
            self.user_id,
            self.money,
        )

        if res["success"]:
            done = get_container_view("✅ 결제 완료", f"주문번호: `{res['order_id']}`", 0x57F287)
        else:
            done = get_container_view("❌ 결제 실패", res["message"], 0xED4245)

        await it.edit_original_response(view=await done.build())


# ── 게임패스 선택 ─────────────────────────────────────────────────────────────
class PassSelectView(ui.LayoutView):
    def __init__(self, passes: list[dict], user_id: int | str):
        super().__init__(timeout=60)
        self.passes = passes
        self.user_id = user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142> 게임패스 선택\n"
            "-# - 구매할 게임패스를 선택하세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        select = ui.Select(placeholder="게임패스를 선택해주세요")
        for p in self.passes[:25]:
            p_id = p.get("id")
            p_name = p.get("name") or "이름 없음"
            p_price = p.get("price", 0)
            if p_id is not None:
                select.add_option(
                    label=f"{p_name[:80]} ({p_price:,} R$)",
                    value=str(p_id),
                )

        select.callback = self.on_select
        con.add_item(ui.ActionRow().add_item(select))

        self.clear_items()
        self.add_item(con)
        return self

    async def on_select(self, it: discord.Interaction):
        selected_id = int(it.data["values"][0])
        pass_data = next(
            (p for p in self.passes if p.get("id") == selected_id), None
        )
        if not pass_data:
            await it.response.send_message("오류: 선택한 게임패스를 찾을 수 없습니다.", ephemeral=True)
            return

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r = cur.fetchone()
        rate = int(r[0]) if r else 1000
        money = int((pass_data.get("price", 0) / rate) * 10000)

        view = FinalBuyView(pass_data, money, it.user.id)
        await it.response.edit_message(view=await view.build())


# ── 게임 선택 ─────────────────────────────────────────────────────────────────
class PlaceSelectView(ui.LayoutView):
    def __init__(self, places: list[dict], user_id: int | str):
        super().__init__(timeout=60)
        self.places = places
        self.user_id = user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142> 게임 선택\n"
            "-# - 게임패스를 구매할 게임을 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        seen: set[int] = set()
        options = []
        for p in self.places:
            u_id = p.get("id")
            if u_id and u_id not in seen and len(seen) < 25:
                options.append(p)
                seen.add(u_id)

        if not options:
            con.add_item(ui.TextDisplay("⚠️ 선택 가능한 공개 게임이 없습니다."))
        else:
            select = ui.Select(placeholder="게임을 선택해주세요")
            for p in options:
                select.add_option(
                    label=p["name"][:100],
                    value=str(p["id"]),
                )
            select.callback = self.on_select
            con.add_item(ui.ActionRow().add_item(select))

        self.clear_items()
        self.add_item(con)
        return self

    async def on_select(self, it: discord.Interaction):
        """게임 선택 → 게임패스 목록 조회 → PassSelectView 표시"""
        universe_id = int(it.data["values"][0])

        loading = get_container_view("⌛ 조회 중", "게임패스 목록을 불러오는 중...", 0xFEE75C)
        await it.response.edit_message(view=await loading.build())

        loop = asyncio.get_running_loop()
        api = RobloxAPI()  # 게임패스 목록은 인증 불필요
        passes = await loop.run_in_executor(None, api.get_place_gamepasses, universe_id)

        if not passes:
            fail = get_container_view("❌ 결과 없음", "이 게임에 판매 중인 게임패스가 없습니다.", 0xED4245)
            await it.edit_original_response(view=await fail.build())
            return

        view = PassSelectView(passes, self.user_id)
        await it.edit_original_response(view=await view.build())


# ── 닉네임 검색 모달 ──────────────────────────────────────────────────────────
class NicknameSearchModal(ui.Modal, title="유저 검색"):
    nick_input = ui.TextInput(
        label="로블록스 닉네임",
        placeholder="로블록스 닉네임을 정확하게 입력해주세요",
        required=True,
        max_length=20,
    )

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)

        loop = asyncio.get_running_loop()
        api = RobloxAPI()

        # 유저 ID 조회 (블로킹 → executor)
        user_id: int | None = await loop.run_in_executor(
            None, api.get_user_id, self.nick_input.value.strip()
        )
        if not user_id:
            fail = get_container_view("❌ 실패", "유저를 찾을 수 없습니다.", 0xED4245)
            await it.followup.send(view=await fail.build(), ephemeral=True)
            return

        # 게임 목록 조회
        places: list[dict] = await loop.run_in_executor(
            None, api.get_user_places, user_id
        )
        if not places:
            fail = get_container_view("❌ 결과 없음", "공개된 게임이 없습니다.", 0xED4245)
            await it.followup.send(view=await fail.build(), ephemeral=True)
            return

        view = PlaceSelectView(places, it.user.id)
        await it.followup.send(view=await view.build(), ephemeral=True)
