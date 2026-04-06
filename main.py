            fee_percent = COIN_FEE.get(self.coin, 0)
            final_amount = int(krw_amount * (1 - fee_percent / 100))

            con.add_item(ui.TextDisplay(
                f"### <:acy2:1489883409001091142>  코인 결제 정보\n"
                f"-# - **코인**: {self.coin_name} ({self.coin_symbol})\n"
                f"-# - **결제 금액**: {krw_amount:,}원\n"
                f"-# - **수수료**: {fee_percent}% (-{krw_amount - final_amount:,}원)\n"
                f"-# - **실제 충전**: {final_amount:,}원\n"
                f"-# - **결제 금액**: {pay_amount} {self.coin_symbol}\n"
                f"-# - **결제 주소**: `{pay_address}`\n"
                f"-# - **주문 ID**: `{order_id}`\n"
                f"-# ⚠️ 위 주소로 정확한 금액을 전송해주세요\n"
                f"-# ⚠️ 입금 확인까지 최대 10분 소요될 수 있습니다"
            ))
