            if products:
                item_text = "\n".join([
                    f"<:dot_white:1482000567562928271> 제품: {p[0]}\n"
                    f"<:dot_white:1482000567562928271> 가격: {p[1]:,}원\n"
                    f"<:dot_white:1482000567562928271> 재고: {p[2]}개 / 누적 판매: {p[3]}개" 
                    for p in products
                ])
            else:
                item_text = "제품이 없습니다"
            res_con = ui.Container(ui.TextDisplay(f"## {selected} 제품 목록"), accent_color=0xffffff)
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.TextDisplay(f"{item_text}"))
            res_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            res_con.add_item(ui.ActionRow(cat_select))
            
            await interaction.response.edit_message(view=ui.LayoutView().add_item(res_con))
