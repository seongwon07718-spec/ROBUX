            selected_id = int(inter.data["values"][0])
            pass_data = next((p for p in passes if p.get("id") == selected_id), None)

            if not pass_data:
                await inter.response.send_message("오류가 발생했습니다.", ephemeral=True)
                return

            # 할인율 조회
            with sqlite3.connect(DATABASE) as conn:
                cur = conn.cursor()

                cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
                r = cur.fetchone()
                rate = int(r[0]) if r else 1000

                cur.execute(
                    "SELECT value FROM config WHERE key = ?",
                    (f"discount_{inter.user.id}",)
                )
                d = cur.fetchone()
                discount = int(d[0]) if d else 0

            base_money = int((pass_data.get("price", 0) / rate) * 10000)
            final_money = int(base_money * (1 - discount / 100)) if discount > 0 else base_money

            discount_text = (
                f"-# - **할인율**: {discount}%\n"
                f"-# - **원래 가격**: ~~{base_money:,}원~~\n"
                f"-# - **최종 가격**: {final_money:,}원"
            ) if discount > 0 else (
                f"-# - **결제 금액**: {final_money:,}원"
            )

            result_view = ui.LayoutView(timeout=60)
            result_con = ui.Container()
            result_con.accent_color = 0x5865F2

            result_con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  선물 정보 확인\n"
                f"-# - **선물 대상**: {target_name}\n"
                f"-# - **게임**: {game_name}\n"
                f"-# - **게임패스**: {pass_data.get('name', '이름없음')}\n"
                f"-# - **가격**: {pass_data.get('price', 0):,}로벅스\n"
                f"{discount_text}"
            ))

            result_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            proceed_btn = ui.Button(
                label="진행하기",
                style=discord.ButtonStyle.gray,
                emoji="<:success:1489875582874554429>",
                custom_id=str(uuid.uuid4()).replace("-", "")[:40]
            )
