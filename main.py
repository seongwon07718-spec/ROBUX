    async def do_buy(self, it: discord.Interaction):
        start_time = asyncio.get_event_loop().time()
        await it.response.edit_message(
            view=await get_container_view(
                "<a:1792loading.:1487444148716965949> 처리 중",
                "-# - 로블록스 서버 API 연결 중\n-# - 구매를 진행하는데 약간의 시간이 소요될 수 있습니다",
                0x57F287
            )
        )
        loop = asyncio.get_running_loop()
        from buy_gamepass import process_manual_buy_selenium
        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money
        )
        elapsed = round(asyncio.get_event_loop().time() - start_time, 1)

        if res["success"]:
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0x57F287
            con.add_item(ui.TextDisplay(
                f"### ✅ 결제 완료\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - **가격**: {self.pass_info.get('price', 0):,} R$\n"
                f"-# - **결제금액**: {self.money:,}원\n"
                f"-# - **처리시간**: {elapsed}초\n"
                f"-# - **거래ID**: `{res['order_id']}`"
            ))
            view.add_item(con)
            await it.edit_original_response(view=view)
        else:
            await it.edit_original_response(
                view=await get_container_view(
                    "❌ 결제 실패",
                    f"-# {res['message']}",
                    0xED4245
                )
            )
