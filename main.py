class NicknameSearchModal(ui.Modal, title="유저 검색"):
    nick_input = ui.TextInput(label="로블록스 닉네임", placeholder="로블록스 닉네임을 정확하게 입력해주세요", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        api = RobloxAPI()
        user_id = api.get_user_id(self.nick_input.value.strip())
        
        if not user_id:
            return await it.followup.send(view=get_container_view("❌ 실패", "-# - 유저를 찾을 수 없습니다", 0xED4245), ephemeral=True)
        
        places = api.get_user_places(user_id)
        if not places:
            return await it.followup.send(view=get_container_view("❌ 결과 없음", "-# - 공개된 게임이 없습니다", 0xED4245), ephemeral=True)
            
        view = PlaceSelectView(places, it.user.id)
        await it.followup.send(view=await view.build(), ephemeral=True)
