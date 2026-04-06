    async def do_buy(self, it: discord.Interaction):

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM config WHERE key = 'maintenance'")
            m = cur.fetchone()

        if m and m[0] == "1":
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  점검 중",
                    "-# - 현재 점검 중입니다\n-# - 잠시 후 다시 시도해주세요",
                    0xED4245
                )
            )
            return

        start_time = asyncio.get_event_loop().time()
        # 나머지 기존 코드...
