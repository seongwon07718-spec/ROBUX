            # 구매 로그
            try:
                log_view = ui.LayoutView(timeout=None)
                log_con = ui.Container()
                log_con.accent_color = 0x57F287
                log_con.add_item(ui.TextDisplay(
                    f"### <:acy2:1489883409001091142>  구매 로그\n"
                    f"-# - **유저**: {it.user.mention}\n"
                    f"-# - **게임패스**: {self.pass_info.get('name', '알 수 없음')}\n"
                    f"-# - **로벅스**: {self.pass_info.get('price', 0):,}로벅스\n"
                    f"-# - **결제금액**: {self.money:,}원\n"
                    f"-# - **처리시간**: {elapsed}초\n"
                    f"-# - **거래ID**: `{res['order_id']}`"
                ))
                log_view.add_item(log_con)
                await send_log("purchase_log", log_view)
            except Exception as e:
                print(f"[구매로그 실패] {e}")
