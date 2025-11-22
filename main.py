        elif interaction.custom_id.startswith("calc_modal_"):
            try:
                # 입력값 파싱
                raw = interaction.text_values.get("calc_amount", "").replace(",", "").replace("원", "").strip()
                try:
                    input_amount = int(raw)
                except Exception:
                    await interaction.response.send_message("금액을 숫자로 입력해주세요. 예: 100000", ephemeral=True)
                    return

                if input_amount <= 0:
                    await interaction.response.send_message("금액은 1원 이상이어야 합니다.", ephemeral=True)
                    return

                # 실시간 수치 조회
                krw_rate = get_exchange_rate()  # USD -> KRW 환율
                kimchi_pct = coin.get_kimchi_premium()  # 김치프리미엄 %
                try:
                    fee_rate = get_service_fee_rate()  # 서비스 수수료율 (0.xx 형태)
                except Exception:
                    fee_rate = service_fee_rate

                # 수수료(원화)
                fee_krw = int(round(input_amount * fee_rate))

                # 김프 반영 환율 (요청대로 김프는 항상 포함)
                adjusted_krw_rate = krw_rate * (1 + (kimchi_pct / 100.0))

                # 수수료 차감 후 실입금(원화)
                after_fee_krw = input_amount - fee_krw

                # 목표 실입금을 얻기 위해 결제해야 할 총액(gross)
                if 1 - fee_rate > 0:
                    gross_needed = int(math.ceil(input_amount / (1 - fee_rate)))
                else:
                    gross_needed = input_amount + fee_krw

                # 임베드 구성
                import disnake
                embed = disnake.Embed(title="수수료 계산 결과", color=0x1abc9c)
                
                embed.add_field(
                    name=f"{input_amount:,}원 충전시",
                    value=f"약 ₩{after_fee_krw:,}원 (수수료 {fee_rate*100:.2f}% 포함)",
                    inline=False
                )

                embed.add_field(
                    name=f"{gross_needed:,}원 결제시",
                    value=f"약 ₩{input_amount:,}원 (결제 후 수수료 차감된 금액)",
                    inline=False
                )

                embed.add_field(
                    name="기준 정보",
                    value=(
                        f"기준 환율(USD→KRW): {krw_rate:,}\n"
                        f"김치프리미엄: {kimchi_pct:.2f}%\n"
                        f"김프 반영 환율: {adjusted_krw_rate:,.4f}\n"
                        f"적용 수수료율: {fee_rate*100:.2f}%"
                    ),
                    inline=False
                )

                embed.set_footer(text=f"계산 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"계산기 모달 처리 오류: {e}")
                try:
                    await interaction.response.send_message("계산 중 오류가 발생했습니다.", ephemeral=True)
                except:
                    pass
