        elif interaction.custom_id.startswith("calc_modal_"):
            try:
                # 1) 입력값 파싱
                raw = interaction.text_values.get("calc_amount", "").replace(",", "").replace("원", "").strip()
                try:
                    input_amount = int(raw)
                except Exception:
                    await interaction.response.send_message("금액을 숫자로 입력해주세요. 예: 100000", ephemeral=True)
                    return

                if input_amount <= 0:
                    await interaction.response.send_message("금액은 1원 이상이어야 합니다.", ephemeral=True)
                    return

                # 2) 실시간 값 조회
                krw_rate = get_exchange_rate()  # USD -> KRW 환율
                kimchi_pct = coin.get_kimchi_premium()  # 김치프리미엄 %
                try:
                    fee_rate = get_service_fee_rate()  # 서비스 수수료율 (0.xx 형태)
                except Exception:
                    fee_rate = service_fee_rate

                # 3) 수수료/김프 금액 계산 (원화 기준)
                fee_krw = int(round(input_amount * fee_rate))                      # 서비스 수수료 (원)
                kimchi_krw = int(round(input_amount * (kimchi_pct / 100.0)))       # 김치프리미엄을 금액 비율로 환산한 값 (원)
                total_deduction = fee_krw + kimchi_krw                             # 총 차감액
                net_received = input_amount - total_deduction                     # 수수료+김프 차감 후 실입금(원화)

                # 4) 목표 실입금을 얻기 위해 결제해야 할 총액(gross) 계산 (수수료만 고려하여 역산)
                #    김프는 시세 영향이므로 gross 계산에서는 서비스 수수료만 고려하는 경우가 일반적입니다.
                if 1 - fee_rate > 0:
                    gross_needed = int(math.ceil(input_amount / (1 - fee_rate)))
                else:
                    gross_needed = input_amount + fee_krw

                # 5) 임베드 구성 (ephemeral)
                import disnake
                embed = disnake.Embed(title="수수료 계산 결과", color=0x1abc9c)

                # 메인 결과: 입력 -> 실입금(수수료+김프 포함 차감)
                embed.add_field(
                    name=f"{input_amount:,}원 충전시",
                    value=f"약 ₩{net_received:,}원 (수수료 + 김프 포함 적용)",
                    inline=False
                )

                # 차감 상세
                embed.add_field(
                    name="차감 상세 (수수료 + 김프)",
                    value=(
                        f"수수료 ({fee_rate*100:.2f}%): ₩{fee_krw:,}\n"
                        f"김치프리미엄 ({kimchi_pct:.2f}%): ₩{kimchi_krw:,}\n"
                        f"총 차감액: ₩{total_deduction:,}"
                    ),
                    inline=False
                )

                # gross 예시 (사용자가 net을 목표로 할 때 결제해야 할 총액)
                embed.add_field(
                    name=f"{gross_needed:,}원 결제시",
                    value=f"약 ₩{input_amount:,}원 (결제 후 서비스 수수료 차감된 금액)",
                    inline=False
                )

                # 보조 정보: 환율·김프·수수료율·시간
                embed.add_field(
                    name="기준 정보",
                    value=(
                        f"기준 환율(USD→KRW): {krw_rate:,}\n"
                        f"김치프리미엄: {kimchi_pct:.2f}%\n"
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
