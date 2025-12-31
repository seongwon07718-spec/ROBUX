    # 추가: 유저 ID 입력 시 자동 초대 로직 (10초 후 삭제 기능 포함)
    async def on_message(self, message):
        if message.author.bot: return
        if isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("중개-"):
            # 입력된 내용이 17~20자리 숫자(ID)인 경우
            if message.content.isdigit() and 17 <= len(message.content) <= 20:
                try:
                    target_user = await message.guild.fetch_member(int(message.content))
                    # 채널 권한 부여
                    await message.channel.set_permissions(target_user, read_messages=True, send_messages=True, embed_links=True, attach_files=True)
                    
                    # 초대된 유저 ID 저장 (Topic 활용)
                    await message.channel.edit(topic=f"invited:{target_user.id}")
                    
                    # 1. 초대 성공 임베드 전송 (10초 뒤 자동 삭제)
                    success_msg = await message.channel.send(
                        embed=discord.Embed(description=f"**{target_user.mention}님이 초대되었습니다**", color=0xffffff),
                        delete_after=10.0 # 10초 후 삭제
                    )
                    
                    # 2. 유저가 입력한 ID 숫자 메시지도 삭제 (선택 사항)
                    try:
                        await message.delete(delay=10.0)
                    except:
                        pass # 봇에게 메시지 관리 권한이 없을 경우 대비
                        
                except Exception as e:
                    # 유저를 찾지 못했을 때 안내 (이것도 5초 뒤 삭제)
                    fail_msg = await message.channel.send(f"❌ 유저를 찾을 수 없습니다: {e}", delete_after=5.0)
        
        await self.process_commands(message)
