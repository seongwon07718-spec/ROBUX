    async def do_buy(self, it: discord.Interaction):

        # 도배 방지
        now = asyncio.get_event_loop().time()
        last = purchase_cooldown.get(self.user_id, 0)
        if now - last < COOLDOWN_SECONDS:
            remain = int(COOLDOWN_SECONDS - (now - last))
            await it.response.edit_message(
                view=await get_container_view(
                    "<:downvote:1489930277450158080>  잠시 기다려주세요",
                    f"-# - {remain}초 후에 다시 시도할 수 있습니다",
                    0xED4245
                )
            )
            return
        purchase_cooldown[self.user_id] = now

        # 나머지 기존 코드...
