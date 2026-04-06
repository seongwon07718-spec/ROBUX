class CoinChargeModal(ui.Modal, title="코인 결제"):

    amount = ui.TextInput(
        label="충전 금액 (원)",
        placeholder="충전할 금액을 입력해주세요 (원)",
        min_length=3
    )

    def __init__(self, coin: str, coin_name: str, coin_symbol: str):
        super().__init__(title=f"코인 결제 - {coin_name}")
        self.coin = coin
        self.coin_name = coin_name
        self.coin_symbol = coin_symbol

    async def on_submit(self, it: discord.Interaction):

        try:
            krw_amount = int(self.amount.value.replace(",", ""))
        except ValueError:
            await it.response.send_message(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 숫자만 입력해주세요", 0xED4245),
                ephemeral=True
            )
            return

        await it.response.send_message(
            view=await get_container_view(
                "<a:1792loading:1487444148716965949>  결제 API 설정 중",
                "-# - 결제 주소를 생성하는 중입니다...",
                0x5865F2
            ),
            ephemeral=True
        )

        # NOWPayments API로 결제 주소 생성
        try:
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM config WHERE key = 'nowpayments_key'")
                key_row = cur.fetchone()

            if not key_row:
                await it.edit_original_response(
                    view=await get_container_view("<:downvote:1489930277450158080>  오류", "-# - 코인 결제가 설정되지 않았습니다", 0xED4245)
                )
                return

            api_key = key_row[0]

            # 원화 → USD 환율 계산
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.exchangerate-api.com/v4/latest/KRW") as resp:
                    rate_data = await resp.json()
                    usd_rate = rate_data["rates"]["USD"]

            usd_amount = round(krw_amount * usd_rate, 2)

            # NOWPayments 결제 생성
            order_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.nowpayments.io/v1/payment",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "price_amount": usd_amount,
                        "price_currency": "usd",
                        "pay_currency": self.coin,
                        "order_id": order_id,
                        "order_description": f"Robux {krw_amount}원 충전"
                    }
                ) as resp:
                    data = await resp.json()

            if "pay_address" not in data:
                await it.edit_original_response(
                    view=await get_container_view("<:downvote:1489930277450158080>  오류", f"-# - 결제 주소 생성 실패", 0xED4245)
                )
                return

            pay_address = data["pay_address"]
            pay_amount = data["pay_amount"]
            payment_id = data["payment_id"]

            # DB에 결제 정보 저장
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'pending')",
                    (order_id, str(it.user.id), krw_amount, 0)
                )
                cur.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (f"coin_payment_{payment_id}", f"{it.user.id}_{krw_amount}_{order_id}")
                )
                conn.commit()

            # 결제 주소 표시
            view = ui.LayoutView(timeout=None)
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  코인 결제 정보\n"
                f"-# - **코인**: {self.coin_name} ({self.coin_symbol})\n"
                f"-# - **충전 금액**: {krw_amount:,}원\n"
                f"-# - **결제 금액**: {pay_amount} {self.coin_symbol}\n"
                f"-# - **결제 주소**: `{pay_address}`\n"
                f"-# - **주문 ID**: `{order_id}`\n"
                f"-# ⚠️ 위 주소로 정확한 금액을 전송해주세요\n"
                f"-# ⚠️ 입금 확인까지 최대 10분 소요될 수 있습니다"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            copy_btn = ui.Button(
                label="주소 복사",
                style=discord.ButtonStyle.gray,
                emoji="<:success:1489875582874554429>"
            )

            async def copy_cb(inter: discord.Interaction):
                await inter.response.send_message(content=f"`{pay_address}`", ephemeral=True)

            copy_btn.callback = copy_cb
            con.add_item(ui.ActionRow(copy_btn))
            view.add_item(con)
            await it.edit_original_response(view=view)

            # 백그라운드에서 입금 확인
            asyncio.create_task(check_coin_payment(it, payment_id, krw_amount, order_id, self.coin_name))

        except Exception as e:
            await it.edit_original_response(
                view=await get_container_view("<:downvote:1489930277450158080>  오류", f"-# - 오류가 발생했습니다: {e}", 0xED4245)
            )


async def check_coin_payment(it: discord.Interaction, payment_id: str, krw_amount: int, order_id: str, coin_name: str):
    """백그라운드에서 코인 입금 확인"""

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'nowpayments_key'")
        key_row = cur.fetchone()

    if not key_row:
        return

    api_key = key_row[0]

    # 30분 동안 확인 (2분마다)
    for _ in range(15):
        await asyncio.sleep(120)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.nowpayments.io/v1/payment/{payment_id}",
                    headers={"x-api-key": api_key}
                ) as resp:
                    data = await resp.json()

            status = data.get("payment_status")

            if status in ("finished", "confirmed", "sending"):
                # 충전 처리
                with sqlite3.connect(DATABASE) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                        (str(it.user.id), krw_amount, krw_amount)
                    )
                    cur.execute("UPDATE orders SET status = 'charge' WHERE order_id = ?", (order_id,))
                    conn.commit()

                try:
                    await it.edit_original_response(
                        view=await get_container_view(
                            "<:upvote:1489930275868770305>  충전 완료",
                            f"-# - **코인**: {coin_name}\n"
                            f"-# - **충전 금액**: {krw_amount:,}원\n"
                            f"-# - **주문 ID**: `{order_id}`",
                            0x57F287
                        )
                    )
                except Exception:
                    pass

                try:
                    await it.user.send(
                        f"<:acy2:1489883409001091142> **코인 충전 완료**\n"
                        f"- 코인: {coin_name}\n"
                        f"- 충전 금액: {krw_amount:,}원\n"
                        f"- 주문 ID: `{order_id}`"
                    )
                except Exception:
                    pass

                return

            elif status == "failed" or status == "expired":
                try:
                    await it.edit_original_response(
                        view=await get_container_view(
                            "<:downvote:1489930277450158080>  결제 실패",
                            f"-# - 결제가 실패하거나 만료되었습니다\n-# - 다시 시도해주세요",
                            0xED4245
                        )
                    )
                except Exception:
                    pass
                return

        except Exception as e:
            print(f"[코인결제 확인 실패] {e}")

    # 30분 초과
    try:
        await it.edit_original_response(
            view=await get_container_view(
                "<:downvote:1489930277450158080>  시간 초과",
                "-# - 30분 내에 입금이 확인되지 않았습니다\n-# - 입금하셨다면 관리자에게 문의해주세요",
                0xED4245
            )
        )
    except Exception:
        pass
