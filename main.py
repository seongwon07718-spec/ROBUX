class GamepassConfirmView(ui.LayoutView):
    def __init__(self, info, money, user_id):
        super().__init__(timeout=120)
        self.info, self.money, self.user_id = info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        price_info = (
            f"-# - **상품**: {self.info['name']}\n"
            f"-# - **가격**: {self.info['price']:,} 로벅스\n"
            f"-# - **금액**: {self.money:,}원"
        )
        con.add_item(ui.TextDisplay(f"### <:acy2:1489883409001091142>  구매 확인\n{price_info}"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        row = ui.ActionRow()
        btn_confirm = ui.Button(label="진행", style=discord.ButtonStyle.gray, emoji="<:upvote:1489930275868770305>")
        btn_confirm.callback = self.self_confirm
        btn_cancel = ui.Button(label="취소", style=discord.ButtonStyle.gray, emoji="<:downvote:1489930277450158080>")
        btn_cancel.callback = self.self_cancel
        row.add_item(btn_confirm)
        row.add_item(btn_cancel)
        con.add_item(row)
        self.clear_items()
        self.add_item(con)
        return self

    async def self_confirm(self, it: discord.Interaction):
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (self.user_id,))
        user_row = cur.fetchone()
        
        if not user_row or user_row[0] < self.money:
            conn.close()
            return await it.response.edit_message(view=get_container_view("❌ 잔액 부족", "충전 후 시도해주세요.", 0xED4245))

        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "구매를 진행 중입니다...", 0xFEE75C))

        result = purchase_gamepass(self.info['productId'], self.info['price'], self.info['sellerId'])
        
        if result["success"]:
            order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (self.money, self.user_id))
            cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                        (order_id, self.user_id, self.money, self.info['price']))
            conn.commit()
            await it.edit_original_response(view=get_container_view("✅ 구매 성공", f"주문번호: `{order_id}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 구매 실패", f"사유: `{result['message']}`", 0xED4245))
        conn.close()

    async def self_cancel(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("취소됨", "구매가 취소되었습니다.", 0x99AAB5))

class GamepassModal(ui.Modal, title="게임패스 구매"):
    id_input = ui.TextInput(label="아이디 또는 링크", placeholder="여기에 입력하세요.", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        pass_id = extract_pass_id(self.id_input.value.strip())
        if not pass_id:
            return await it.followup.send(view=get_container_view("❌ 오류", "ID가 올바르지 않습니다.", 0xED4245), ephemeral=True)

        info = fetch_gamepass_details(pass_id)
        if not info or not info.get('productId'):
            return await it.followup.send(view=get_container_view("❌ 조회 실패", "정보를 가져오지 못했습니다.", 0xED4245), ephemeral=True)

        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r_row = cur.fetchone(); conn.close()
        rate = int(r_row[0]) if r_row else 1000
        money = int((info['price'] / rate) * 10000) if info['price'] > 0 else 0

        view_obj = GamepassConfirmView(info, money, it.user.id)
        await it.followup.send(view=await view_obj.build(), ephemeral=True)
