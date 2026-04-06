    async def main_callback(self, it: discord.Interaction):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay(
            "### <:acy2:1489883409001091142>  충전 수단\n"
            "-# - 원하시는 **충전 방식**을 선택해주세요"
        ))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")
        btn_coin = ui.Button(label="코인결제", style=discord.ButtonStyle.gray, emoji="<:opt_online:1489872305138962452>")

        async def bank_cb(i: discord.Interaction):
            await i.response.send_modal(ChargeModal())

        async def coin_cb(i: discord.Interaction):
            view = ui.LayoutView(timeout=60)
            con = ui.Container()
            con.accent_color = 0x5865F2
            con.add_item(ui.TextDisplay(
                "### <:acy2:1489883409001091142>  코인 결제\n"
                "-# - 결제할 코인을 선택해주세요"
            ))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            select = ui.Select(
                placeholder="코인을 선택해주세요",
                custom_id=str(uuid.uuid4()).replace("-", "")[:40]
            )
            select.add_option(label="라이트코인 (LTC)", value="ltc", emoji="🪙")
            select.add_option(label="트론 (TRX)", value="trx", emoji="🪙")
            select.add_option(label="비트코인 (BTC)", value="btc", emoji="🪙")
            select.add_option(label="솔라나 (SOL)", value="sol", emoji="🪙")

            async def on_coin_select(inter: discord.Interaction):
                coin = inter.data["values"][0]
                coin_name = COIN_LIST[coin][0]
                coin_symbol = COIN_LIST[coin][1]

                # 금액 입력 모달
                await inter.response.send_modal(CoinChargeModal(coin, coin_name, coin_symbol))

            select.callback = on_coin_select
            con.add_item(ui.ActionRow(select))
            view.add_item(con)
            await i.response.send_message(view=view, ephemeral=True)

        btn_bank.callback = bank_cb
        btn_coin.callback = coin_cb
        con.add_item(ui.ActionRow(btn_bank, btn_coin))
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
