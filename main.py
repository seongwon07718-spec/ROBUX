    async def do_buy(self, it: discord.Interaction):
        await it.response.edit_message(
            view=await get_container_view(
                "<a:1792loading.:1487444148716965949> 처리 중",
                "-# - 로블록스 서버 API 연결 중",
                0x57F287
            )
        )
        loop = asyncio.get_running_loop()
        from buy_gamepass import process_manual_buy_selenium
        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money
        )

        if res["success"]:
            screenshot = res.get("screenshot")
            if screenshot and os.path.exists(screenshot):
                await it.edit_original_response(
                    content=f"✅ **결제 완료** | 주문번호: `{res['order_id']}`",
                    attachments=[discord.File(screenshot, filename="success.png")]
                )
            else:
                await it.edit_original_response(
                    view=await get_container_view(
                        "✅ 결제 완료",
                        f"-# 주문번호: `{res['order_id']}`",
                        0x57F287
                    )
                )
        else:
            await it.edit_original_response(
                view=await get_container_view(
                    "❌ 결제 실패",
                    f"-# {res['message']}",
                    0xED4245
                )
            )
