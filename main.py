        if res["success"]:
            screenshot = res.get("screenshot")
            if screenshot and os.path.exists(screenshot):
                view = ui.LayoutView()
                con = ui.Container()
                con.accent_color = 0x57F287
                con.add_item(ui.TextDisplay(
                    f"### ✅ 결제 완료\n"
                    f"-# 주문번호: `{res['order_id']}`"
                ))
                con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
                gallery = ui.MediaGallery(
                    items=[
                        ui.MediaGallery.Item(
                            media=discord.UnfurledMediaItem(url="attachment://success.png")
                        )
                    ]
                )
                con.add_item(gallery)
                view.add_item(con)
                await it.edit_original_response(
                    view=view,
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
