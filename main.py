import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def make_card_message():
    return {
        "content": "",
        "components": [
            {
                "type": "card",
                "children": [
                    {
                        "type": "card_header",
                        "title": "상점 카드",
                        "subtitle": "로벅스 상품 안내"
                    },
                    {
                        "type": "section",
                        "text": "상품을 고르고 아래 버튼을 눌러줘."
                    },
                    {
                        "type": "field_grid",
                        "fields": [
                            {"label": "상품", "value": "Robux 100", "inline": True},
                            {"label": "가격", "value": "100 크레딧", "inline": True},
                            {"label": "상품", "value": "Robux 500", "inline": True},
                            {"label": "가격", "value": "500 크레딧", "inline": True}
                        ]
                    },
                    {
                        "type": "actions",
                        "items": [
                            {"type": "button", "style": "primary", "label": "Robux 100 구매", "custom_id": "shop:buy:rbx100"},
                            {"type": "button", "style": "secondary", "label": "Robux 500 구매", "custom_id": "shop:buy:rbx500"},
                            {"type": "button", "style": "link", "label": "상세 가이드", "url": "https://example.com/shop-guide"}
                        ]
                    }
                ]
            }
        ]
    }

class QtyModal(discord.ui.Modal, title="구매 수량 입력"):
    def __init__(self, sku: str):
        super().__init__(timeout=120)
        self.sku = sku
        self.qty = discord.ui.TextInput(
            label="수량",
            placeholder="1 이상 정수",
            required=True,
            min_length=1,
            max_length=6,
        )
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(str(self.qty.value).strip())
            if qty <= 0:
                raise ValueError
        except Exception:
            await interaction.response.send_message("수량이 올바르지 않아.", ephemeral=True)
            return

        order_id = f"ord-{self.sku}-{qty}"
        await interaction.response.send_message(
            f"주문 완료! SKU: {self.sku}, 수량: {qty}\n주문번호: {order_id}",
            ephemeral=True
        )
        await interaction.followup.send(
            f"[영수증] <@{interaction.user.id}> {self.sku} x {qty} 구매",
            ephemeral=True
        )

@bot.event
async def on_ready():
    print("ready", bot.user)
    # 카드 전송
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    async with aiohttp.ClientSession(headers=headers) as s:
        r = await s.post(url, json=make_card_message())
        print("send card:", r.status, await r.text())

@bot.event
async def on_interaction(interaction: discord.Interaction):
    data = getattr(interaction, "data", {}) or {}
    cid = data.get("custom_id")
    if not cid:
        return
    if cid.startswith("shop:buy:"):
        sku = cid.split(":")[-1]
        # 모달 띄워 수량 입력
        await interaction.response.send_modal(QtyModal(sku))

if __name__ == "__main__":
    if not TOKEN or CHANNEL_ID == 0:
        raise RuntimeError("DISCORD_TOKEN, CHANNEL_ID 환경변수 세팅 필요")
    bot.run(TOKEN)
