# --- [ 구매 후기 작성 모달 ] ---
class ReviewModal(ui.Modal, title="구매 후기 작성"):
    # 별점은 1~5 숫자만 받도록 안내
    rating = ui.TextInput(label="별점 (1~5)", placeholder="숫자 1에서 5 사이로 입력해주세요 (예: 5)", min_length=1, max_length=1)
    content = ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, placeholder="제품에 대한 솔직한 후기를 남겨주세요!", min_length=5, max_length=200)

    def __init__(self, prod_name):
        super().__init__()
        self.prod_name = prod_name

    async def on_submit(self, it: discord.Interaction):
        # 별점 유효성 검사
        if not self.rating.value.isdigit() or not (1 <= int(self.rating.value) <= 5):
            return await it.response.send_message("❌ 별점은 1에서 5 사이의 숫자만 입력 가능합니다.", ephemeral=True)

        stars = "⭐" * int(self.rating.value)
        review_url = WEBHOOK_CONFIG.get("후기")

        if not review_url:
            return await it.response.send_message("❌ 후기 웹훅 설정이 되어있지 않습니다.", ephemeral=True)

        # 후기 컨테이너 디자인
        review_con = ui.Container(ui.TextDisplay(f"## 📝 새로운 구매 후기"), accent_color=0xffd700) # 금색
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"**제품명:** {self.prod_name}\n**작성자:** {it.user.mention}\n**별점:** {stars} ({self.rating.value}점)"))
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"**내용:**\n{self.content.value}"))
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"-# 작성일시: {time.strftime('%Y-%m-%d %H:%M:%S')}"))

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(review_url, session=session)
            view = ui.LayoutView().add_item(review_con)
            await webhook.send(view=view, username="구매 후기 알림")

        await it.response.send_message("✅ 소중한 후기가 성공적으로 등록되었습니다!", ephemeral=True)

# --- [ 기존 PurchaseModal 내 수정 (성공 시 버튼 추가) ] ---
# PurchaseModal의 on_submit 내부 성공 처리 부분만 아래와 같이 수정하세요.

        # ... (중략: 재고/잔액 체크 및 DB 업데이트 완료 후)
        
        res_con = ui.Container(ui.TextDisplay("## 🎉 구매 완료"), accent_color=0x00ff00)
        res_con.add_item(ui.TextDisplay(f"제품: **{self.prod_name}**\n수량: **{buy_count}개**\n\n구매 후기를 남겨주시면 큰 도움이 됩니다!"))
        
        # 후기 작성 버튼 추가
        review_btn = ui.Button(label="구매 후기 작성", style=discord.ButtonStyle.primary, emoji="📝")
        
        async def review_btn_callback(it_btn: discord.Interaction):
            await it_btn.response.send_modal(ReviewModal(self.prod_name))
        
        review_btn.callback = review_btn_callback
        res_con.add_item(ui.ActionRow(review_btn))

        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
