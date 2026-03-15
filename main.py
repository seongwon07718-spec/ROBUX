class ReviewModal(ui.Modal, title="구매 후기 작성"):
    rating = ui.TextInput(label="별점 (1~5)", placeholder="숫자 1~5 입력 (예: 5)", min_length=1, max_length=1)
    content = ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, placeholder="솔직한 후기를 남겨주세요!", min_length=5, max_length=200)

    def __init__(self, prod_name):
        super().__init__()
        self.prod_name = prod_name

    async def on_submit(self, it: discord.Interaction):
        if not self.rating.value.isdigit() or not (1 <= int(self.rating.value) <= 5):
            return await it.response.send_message("❌ 별점은 1에서 5 사이의 숫자만 입력 가능합니다.", ephemeral=True)

        stars = "⭐️" * int(self.rating.value) # 요청하신 이모지로 설정
        review_url = WEBHOOK_CONFIG.get("후기")

        review_con = ui.Container(ui.TextDisplay(f"## 📝 구매 후기 도착!"), accent_color=0xffd700)
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"**제품:** {self.prod_name}\n**작성자:** {it.user.mention}\n**별점:** {stars}"))
        review_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        review_con.add_item(ui.TextDisplay(f"**내용:**\n{self.content.value}"))

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(review_url, session=session)
            await webhook.send(view=ui.LayoutView().add_item(review_con), username="구매 후기 알림")

        await it.response.send_message("✅ 후기가 성공적으로 등록되었습니다!", ephemeral=True)
