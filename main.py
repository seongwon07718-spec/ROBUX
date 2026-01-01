# --- [핵심] 로블록스 자동화 수정 버전 ---
async def start_roblox_automation(interaction, seller_nick):
    channel = interaction.channel
    buyer_id = int(channel.topic.split(":")[1]) if channel.topic else None
    
    status_embed = discord.Embed(title="접속 중", description="**비공개 서버에 접속하여 봇을 세팅 중입니다...**", color=0xffffff)
    status_msg = await interaction.followup.send(embed=status_embed)

    webbrowser.open(ROBLOX_AMP_SERVER)
    
    await asyncio.sleep(20)
    status_embed.description = f"**봇 세팅이 완료되었습니다.**\n\n**[비공개 서버 바로가기]({ROBLOX_AMP_SERVER})**\n\n**판매자님은 접속 후 봇에게 거래를 걸어주세요.**"
    await status_msg.edit(embed=status_embed, view=CallAdminOnlyView())

    try:
        print(f"거래 감지 시작... 대상: {seller_nick}")
        while True:
            # 1. 픽셀 매칭 (오차 범위를 25로 늘려 조금 달라도 인식하게 함)
            if pyautogui.pixelMatchesColor(SCAN_POINT[0], SCAN_POINT[1], SCAN_RGB, tolerance=25):
                print("거래창 감지됨! 닉네임 판독 중...")
                
                # 2. 닉네임 판독 전 잠깐 대기 (창이 완전히 뜨는 시간)
                await asyncio.sleep(0.5)
                
                # 3. 닉네임 OCR 영역 스크린샷 및 판독
                cap = pyautogui.screenshot(region=NICK_REGION)
                # 판독 정확도를 높이기 위해 흑백 처리 (Tesseract 성능 향상)
                detected = pytesseract.image_to_string(cap, lang='eng').strip()
                
                print(f"인식된 텍스트: '{detected}'")

                # 4. 닉네임이 포함되어 있는지 확인 (대소문자 무시)
                if seller_nick.lower() in detected.lower():
                    print("판매자 일치! 수락 버튼 클릭")
                    pyautogui.click(ACCEPT_BTN)
                    break
                else:
                    # 닉네임이 비어있지 않은데 다른 이름이라면 거절
                    if len(detected) > 2:
                        print("판매자 불일치로 거절합니다.")
                        pyautogui.click(REJECT_BTN)
            
            await asyncio.sleep(0.5) # 감시 주기

        # 이후 아이템 검수 로직 동일...
