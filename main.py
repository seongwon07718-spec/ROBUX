    # ── 게임패스 구매 ─────────────────────────────────────────────────────────
    def buy_gamepass(self, pass_id: int) -> dict:
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
            result = resp.json()
        except Exception:
            return {"purchased": False, "reason": f"HTTP {resp.status_code}"}

        return result


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
        reason = (
            result.get("reason")
            or result.get("errorMessage")
            or result.get("reason")
            or "구매 조건이 맞지 않습니다."
        )
        return {"success": False, "message": reason}

    order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (money, user_id),
        )
        cur.execute(
            "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
            (order_id, user_id, money, result.get("currency", {}).get("robux", 0)),
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
        self._build_ui()

    def _build_ui(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = (
            "### <:acy2:1489883409001091142> 최종 단계\n"
            f"-# - **게임패스 이름**: {self.pass_info.get('name', '알 수 없음')}\n"
            f"-# - **로벅스**: {self.pass_info.get('price', 0):,}로벅스\n"
            f"-# - **차감금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(text))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        btn = ui.Button(label="진행하기", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn.callback = self.do_buy
        con.add_item(ui.ActionRow().add_item(btn))
        self.add_item(con)

    async def do_buy(self, it: discord.Interaction):
        await it.response.edit_message(
            view=await get_container_view("<a:1792loading.:1487444148716965949>  처리 중", "-# - 로블록스 서버 API 연결 중", 0x57F287)
        )
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None, process_manual_buy,
            self.pass_info["id"], self.user_id, self.money
        )
        if res["success"]:
            view = await get_container_view("✅ 결제 완료", f"주문번호: `{res['order_id']}`", 0x57F287)
        else:
            view = await get_container_view("❌ 결제 실패", res["message"], 0xED4245)
        await it.edit_original_response(view=view)
