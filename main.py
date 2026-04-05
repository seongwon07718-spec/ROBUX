    async def on_select(self, it: discord.Interaction):

        selected_id = int(it.data["values"][0])
        pass_data = next((p for p in self.passes if p.get("id") == selected_id), None)

        if not pass_data:
            await it.response.send_message("오류가 발생했습니다.", ephemeral=True)
            return

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()

            # 환율
            cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
            r = cur.fetchone()
            rate = int(r[0]) if r else 1000

            # 할인율
            cur.execute("SELECT value FROM config WHERE key = ?", (f"discount_{it.user.id}",))
            d = cur.fetchone()
            discount = int(d[0]) if d else 0

        # 기본 금액 계산
        base_money = int((pass_data.get("price", 0) / rate) * 10000)

        # 할인 적용
        if discount > 0:
            discounted = int(base_money * (1 - discount / 100))
        else:
            discounted = base_money

        view = FinalBuyView(pass_data, discounted, it.user.id, discount)
        await it.response.edit_message(view=view)
