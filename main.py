@bot.tree.command(name="자판기", description="로벅스 자판기를 전송합니다")
async def spawn_vending(it: discord.Interaction):
    await it.response.send_message(
        view=await get_container_view("<:acy2:1489883409001091142>  자판기", "-# - 자판기가 전송되었습니다", 0x5865F2),
        ephemeral=True
    )
    view = RobuxVending(bot)
    con = await view.build_main_menu()
    msg = await it.channel.send(view=ui.LayoutView().add_item(con))
    bot.vending_msg_info[it.channel_id] = msg.id

    # DB에 저장
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO vending_messages (channel_id, msg_id) VALUES (?, ?)",
            (str(it.channel_id), str(msg.id))
        )
        conn.commit()
