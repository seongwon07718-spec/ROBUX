            conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
            cur.execute("SELECT name, price, stock, sold_count FROM products WHERE category = ?", (selected,))
            products = cur.fetchall(); conn.close()

            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            
            if products:
                for p in products:
                    # 각 제품마다 구분선을 넣고 정보를 추가
                    res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                    item_info = (
                        f"<:dot_white:1482000567562928271> 제품: **{p[0]}**\n"
                        f"<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n"
                        f"<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개"
                    )
                    res_con.add_item(ui.TextDisplay(item_info))
            else:
                res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                res_con.add_item(ui.TextDisplay("등록된 제품이 없습니다."))

            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))
