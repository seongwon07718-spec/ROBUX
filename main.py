# --- VerifyCheckView: 최종 인증 확인 및 역할 부여 뷰 ---
class VerifyCheckView(discord.ui.View):
    def __init__(self, roblox_name, verify_key):
        super().__init__(timeout=None)
        self.roblox_name = roblox_name
        self.verify_key = verify_key

    @discord.ui.button(label="인증 완료하기", style=discord.ButtonStyle.gray)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. 닉네임으로 정확한 User ID를 가져오는 API (POST 방식이 가장 정확함)
        search_url = "https://users.roblox.com/v1/usernames/users"
        search_data = {"usernames": [self.roblox_name], "excludeBannedUsers": True}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(search_url, json=search_data) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if not res_json.get("data"):
                        return await interaction.response.send_message("로블록스 유저 정보를 찾을 수 없습니다.", ephemeral=True)
                    
                    user_id = res_json["data"][0]["id"]
                    
                    # 2. 프로필 소개(Description) 확인 API
                    detail_url = f"https://users.roblox.com/v1/users/{user_id}"
                    async with session.get(detail_url) as detail_resp:
                        if detail_resp.status == 200:
                            detail_data = await detail_resp.json()
                            description = detail_data.get("description", "")
                            
                            # 인증 문구 포함 여부 확인
                            if self.verify_key in description:
                                role = interaction.guild.get_role(VERIFY_ROLE_ID)
                                if role:
                                    await interaction.user.add_roles(role)
                                    embed = discord.Embed(
                                        title="✅ 인증 완료",
                                        description=f"**{self.roblox_name}**님, 인증이 완료되었습니다!\n이제 모든 기능을 이용하실 수 있습니다.",
                                        color=discord.Color.green()
                                    )
                                    # 버튼이 있는 메시지를 수정하여 버튼 제거
                                    await interaction.response.edit_message(embed=embed, view=None)
                                else:
                                    await interaction.response.send_message("서버에 설정된 인증 역할 ID가 올바르지 않습니다. 관리자에게 문의하세요.", ephemeral=True)
                            else:
                                await interaction.response.send_message(
                                    f"❌ 인증 문구를 찾을 수 없습니다.\n\n**작성해야 할 문구:** `{self.verify_key}`\n\n프로필 소개란을 다시 확인해주세요.", 
                                    ephemeral=True
                                )
                        else:
                            await interaction.response.send_message("로블록스 상세 정보를 불러오는 중 오류가 발생했습니다.", ephemeral=True)
                else:
                    await interaction.response.send_message("로블록스 서버와 통신 중 오류가 발생했습니다.", ephemeral=True)
