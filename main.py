import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 카드 v2 페이로드 생성
def make_card_message():
    # 주의: 아래 키/타입 명칭은 “임베드”가 아닌 “카드 v2” 레이아웃을 가정
    # 네 길드/클라에 적용된 스펙 명칭이 다르면 그대로 치환해줘
    return {
        "content": "",  # 카드만 보여주고 싶으면 비워둠
        "components": [
            {
                "type": "card",  # 카드 컨테이너
                "children": [
                    {
                        "type": "card_header",
                        "title": "상점 카드",
                        "subtitle": "로벅스 상품 안내"
                    },
                    {
                        "type": "section",
                        "text": "원하는 상품을 골라 아래 버튼으로 구매 진행해줘."
                    },
                    {
                        "type": "field_grid",
                        "fields": [
                            {"label": "상품", "value": "Robux 100", "inline": True},
                            {"label": "가격", "value": "100 크레딧", "inline": True},
                            {"label": "상품", "value": "Robux 500", "inline": True},
                            {"label": "가격", "value": "500 크레딧", "inline": True},
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
        ],
        "allowed_mentions": {"parse": []}
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
            await interaction.response.send_message("수량이 올바르지 않아 ㅠ 다시 입력해줘.", ephemeral=True)
            return

        order_id = f"ord-{self.sku}-{qty}"
        # 최초 응답
        await interaction.response.send_message(
            f"주문 완료! SKU: {self.sku}, 수량: {qty}\n주문번호: {order_id}",
            ephemeral=True
        )
        # 후속 알림
        await interaction.followup.send(
            f"[영수증] <@{interaction.user.id}> {self.sku} x {qty} 구매",
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f"ready {bot.user}")
    if CHANNEL_ID == 0:
        print("CHANNEL_ID 환경변수 설정 필요")
        return
    # 원시 HTTP로 카드 메시지 전송
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.post(url, json=make_card_message()) as r:
            body = await r.text()
            print("send card:", r.status, body)
            if r.status == 404:
                print("채널을 못 찾았어. CHANNEL_ID 다시 확인 + 봇이 그 길드에 있는지/권한 있는지 체크!")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    # 컴포넌트 v2 버튼 콜백 처리
    data = getattr(interaction, "data", {}) or {}
    cid = data.get("custom_id")
    if not cid:
        return
    if cid.startswith("shop:buy:"):
        sku = cid.split(":")[-1]
        await interaction.response.send_modal(QtyModal(sku))

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN이 비어있어!")
    if CHANNEL_ID == 0:
        raise RuntimeError("CHANNEL_ID 설정해줘!")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
