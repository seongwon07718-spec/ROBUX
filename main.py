    # 주문취소 로그
    try:
        log_view = ui.LayoutView(timeout=None)
        log_con = ui.Container()
        log_con.accent_color = 0xED4245
        log_con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  주문취소 로그\n"
            f"-# - **대상**: {mention}\n"
            f"-# - **거래ID**: `{거래id}`\n"
            f"-# - **복구 금액**: {amount:,}원\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        log_view.add_item(log_con)
        await send_log("cancel_log", log_view)
    except Exception as e:
        print(f"[취소로그 실패] {e}")
