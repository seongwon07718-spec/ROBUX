    async def do_buy(self, it: discord.Interaction):
        await it.response.edit_message(
            view=await get_container_view("<a:1792loading.:1487444148716965949> 처리 중", "-# - 로블록스 서버 API 연결 중", 0x57F287)
        )
        loop = asyncio.get_running_loop()
        # ✅ selenium 함수로 교체
        from buy_gamepass import process_manual_buy_selenium
        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money
        )
        if res["success"]:
            view = await get_container_view("✅ 결제 완료", f"-# 주문번호: `{res['order_id']}`", 0x57F287)
        else:
            view = await get_container_view("❌ 결제 실패", f"-# {res['message']}", 0xED4245)
        await it.edit_original_response(view=view)

    def get_user_id(self, nickname: str) -> int | None:
        resp = self.session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [nickname], "excludeBannedUsers": False},  # ✅ False로
        )
        print(f"[유저검색] status={resp.status_code} body={resp.text}")
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        return data[0].get("id") if data else None

