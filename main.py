import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

# 필수 환경변수
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# 길드 고정 (네 길드)
GUILD_ID = 1419200424636055592

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 카드 v2 메시지 페이로드
def make_card_message():
    # 주의: 아래 키(type/name)는 카드 v2 스타일 예시다.
    # 만약 네 클라/길드 스펙에서 명칭이 다르면 동일 자리의 키 이름만 바꿔주면 된다.
    return {
        "content": "",
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
                        "text": "상품을 고르고 아래 버튼으로 구매를 진행해줘."
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
            await interaction.response.send_message("수량이 올바르지 않아. 1 이상 정수로 입력해줘!", ephemeral=True)
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
    print(f"ready {bot.user} | guild={GUILD_ID}")
    if CHANNEL_ID == 0:
        print("CHANNEL_ID 환경변수 설정 필요")
        return

    # 봇이 해당 길드에 실제로 있는지 확인
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("봇이 1419200424636055592 길드에 없거나, 캐시에서 못 찾았어. 초대/권한 확인해줘.")
    else:
        print(f"길드 확인: {guild.name}")

    # 원시 HTTP로 카드 메시지 전송
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    payload = make_card_message()
    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.post(url, json=payload) as r:
            body = await r.text()
            print("send card:", r.status, body)
            if r.status == 404:
                print("Unknown Channel 10003: CHANNEL_ID 다시 확인 + 봇 권한/길드 일치 확인!")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    # 버튼 인터랙션 처리 (컴포넌트 v2)
    data = getattr(interaction, "data", {}) or {}
    custom_id = data.get("custom_id")
    if not custom_id:
        return

    if custom_id.startswith("shop:buy:"):
        sku = custom_id.split(":")[-1]
        try:
            await interaction.response.send_modal(QtyModal(sku))
        except discord.InteractionResponded:
            # 이미 응답된 경우 대비
            await interaction.followup.send("이미 처리된 인터랙션이야. 다시 시도해줘!", ephemeral=True)

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN이 비어있어!")
    if CHANNEL_ID == 0:
        raise RuntimeError("CHANNEL_ID 설정해줘!")
    # 슬래시 커맨드 동기화 관련 훅은 사용하지 않음 (네 로그의 'shop not found' 원인 제거)
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
