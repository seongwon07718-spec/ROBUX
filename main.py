        elif interaction.component.custom_id == "open_calc_modal":
            # 모달 바로 띄우기 (단일 입력)
            serial_code = random.randint(100000, 999999)
            try:
                await interaction.response.send_modal(CalculatorModal(serial_code))
            except Exception as e:
                logger.error(f"계산기 모달 오픈 오류: {e}")
                try:
                    await interaction.response.send_message("계산기 실행 중 오류가 발생했습니다.", ephemeral=True)
                except:
                    pass
