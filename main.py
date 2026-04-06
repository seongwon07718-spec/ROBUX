    # 할인 설정 로그
    try:
        log_view = ui.LayoutView(timeout=None)
        log_con = ui.Container()
        log_con.accent_color = 0x5865F2
        log_con.add_item(ui.TextDisplay(
            f"### <:acy2:1489883409001091142>  할인 설정 로그\n"
            f"-# - **대상**: {유저.mention}\n"
            f"-# - **할인율**: {할인율}%\n"
            f"-# - **처리자**: {it.user.mention}"
        ))
        log_view.add_item(log_con)
        await send_log("discount_log", log_view)
    except Exception as e:
        print(f"[할인로그 실패] {e}")
