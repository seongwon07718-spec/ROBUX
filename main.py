@bot.tree.command(name="유저복구", description="인증했던 유저들을 서버에 복구하기")
@app_commands.checks.has_permissions(administrator=True)
async def restore(it: discord.Interaction):
    await it.response.send_message("🔄 복구 프로세스를 가동합니다. 잠시만 기다려주세요...", ephemeral=True)
    
    conn = sqlite3.connect('restore_user.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id, access_token FROM users WHERE server_id = ?", (str(it.guild_id),))
    all_users = cur.fetchall()
    conn.close()

    if not all_users:
        return await it.followup.send("❌ 복구할 유저 데이터가 존재하지 않습니다.")

    success, fail = 0, 0
    async with aiohttp.ClientSession() as session:
        for u_id, token in all_users:
            url = f"https://discord.com/api/v10/guilds/{it.guild_id}/members/{u_id}"
            headers = {
                "Authorization": f"Bot {TOKEN}",
                "Content-Type": "application/json"
            }
            async with session.put(url, headers=headers, json={"access_token": token}) as resp:
                if resp.status in [201, 204]:
                    success += 1
                else:
                    fail += 1
                await asyncio.sleep(0.5)
                
    await it.followup.send(f"✅ 복구 완료! (성공: {success}명 / 실패: {fail}명)")
