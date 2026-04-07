        res = await loop.run_in_executor(
            None, process_manual_buy_selenium,
            self.pass_info["id"], self.user_id, self.money,
            self.pass_info.get("roblox_name", ""),   # ✅ 추가
            self.pass_info.get("name", "")            # ✅ 추가
        )
