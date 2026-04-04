class GamepassModal(ui.Modal, title="게임패스 방식"):
    id_input = ui.TextInput(label="게임패스 ID 또는 링크", placeholder="게임패스 ID 또는 링크를 적어주세요", required=True)

    async def on_submit(self, it: discord.Interaction):
        raw_val = self.id_input.value.strip()
        pass_id = extract_pass_id(raw_val)
        
        if not pass_id:
            return await it.response.send_message(view=get_container_view("❌ 인식 오류", "올바른 ID나 링크를 입력해주세요.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
        c_row = cur.fetchone()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone()
        conn.close()

        admin_cookie = c_row[0] if c_row else None
        info = fetch_gamepass_details(pass_id, admin_cookie)
        
        if not info:
            return await it.response.send_message(view=get_container_view("❌ 찾을 수 없음", f"ID `{pass_id}` 정보를 불러올 수 없습니다.", 0xED4245), ephemeral=True)

        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000)

        view_obj = GamepassConfirmView(info, money, it.user.id, admin_cookie)
        await it.response.send_message(view=await view_obj.build(), ephemeral=True)
