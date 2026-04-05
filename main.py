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

        elif res.get("message") and "이미 소유" in res["message"]:
            view = ui.LayoutView()
            con = ui.Container()
            con.accent_color = 0xFEE75C
            con.add_item(ui.TextDisplay(
                f"### ⚠️ 구매 불가\n"
                f"-# - 이미 보유 중인 게임패스입니다.\n"
                f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                f"-# - 다른 게임패스를 선택해주세요."
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
