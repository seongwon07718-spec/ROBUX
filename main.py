import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
GUILD_ID = 1419200424636055592  # 네 서버

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 안전 가드: 채널 검증
async def validate_channel(bot: commands.Bot, channel_id: int) -> tuple[bool, str]:
    ch = bot.get_channel(channel_id)
    if ch is None:
        try:
            ch = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            return False, "채널이 존재하지 않음(NotFound). CHANNEL_ID 다시 확인."
        except discord.Forbidden:
            return False, "채널 조회 권한 없음(Forbidden). 봇 권한 확인."
        except discord.HTTPException as e:
            return False, f"채널 조회 실패(HTTPException): {e}"
    if not isinstance(ch, discord.TextChannel):
        return False, "텍스트 채널 ID가 아님. 일반 텍스트 채널 ID를 넣어."
    if ch.guild.id != GUILD_ID:
        return False, f"길드 불일치: 채널 길드({ch.guild.id}) != 기대 길드({GUILD_ID})"
    perms = ch.permissions_for(ch.guild.me)
    if not perms.send_messages:
        return False, "메시지 보내기 권한 없음. 채널 권한 부여."
    return True, "OK"

# 지금 REST에서 통과되는 표준 컴포넌트 타입으로 구성 (Action Row=1, Button=2, Select=3/5/6/7)
def make_components_like_card():
    # 1) 상단 설명을 content로 카드처럼 연출 (임베드 X)
    # 2) 하단에 버튼/셀렉트 배치
    return [
        {
            "type": 1,  # Action Row
            "components": [
                {
                    "type": 3,  # String Select Menu
                    "custom_id": "shop:select",
                    "placeholder": "상품을 선택해줘",
                    "min_values": 1,
                    "max_values": 1,
                    "options": [
                        {"label": "Robux 100", "value": "rbx100", "description": "100 크레딧"},
                        {"label": "Robux 500", "value": "rbx500", "description": "500 크레딧"},
                        {"label": "Robux 1000", "value": "rbx1k", "description": "1000 크레딧"},
                    ]
                }
            ]
        },
        {
            "type": 1,
            "components": [
                {
                    "type": 2,  # Button
                    "style": 3,  # SUCCESS(초록)
                    "label": "구매",
                    "custom_id": "shop:buy"
                },
                {
                    "type": 2,
                    "style": 2,  # SECONDARY
                    "label": "자세히",
                    "custom_id": "shop:details"
                }
            ]
        }
    ]

# 카드처럼 보이는 본문(임베드 X)
def make_content_like_card(selected=None):
    header = "────────────────────────\n테스트입니다.\n\nPython으로도 Components V2 느낌 살려서 쓸 수 있다? 가능.\nDiscord.py로도 충분히 굴러감.\n────────────────────────"
    if selected:
        header += f"\n선택한 상품: {selected}"
    return header

# 선택 상태를 간단히 메모리로 유지 (실서비스면 캐시/DB)
user_selected = {}  # {user_id: sku}

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
            await interaction.response.send_message("수량이 올바르지 않아. 1 이상 정수로 입력!", ephemeral=True)
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
    print(f"READY {bot.user} | guild={GUILD_ID} | channel={CHANNEL_ID}")
    ok, reason = await validate_channel(bot, CHANNEL_ID)
    if not ok:
        print(f"[차단] 전송 중단: {reason}")
        return

    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    payload = {
        "content": make_content_like_card(),
        "components": make_components_like_card(),
        "allowed_mentions": {"parse": []}
    }

    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.post(url, json=payload) as r:
            body = await r.text()
            print("send:", r.status, body)
            if r.status >= 300:
                print("전송 실패. 위 본문(body) 보고 placeholder/옵션 길이 등 검증해봐.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    data = getattr(interaction, "data", {}) or {}
    cid = data.get("custom_id")
    t = data.get("component_type")

    # 셀렉트 처리
    if cid == "shop:select":
        values = data.get("values") or []
        sku = values[0] if values else None
        if not sku:
            await interaction.response.send_message("선택값 없음. 다시 시도!", ephemeral=True)
            return
        user_selected[interaction.user.id] = sku
        # 메시지 편집으로 카드 텍스트 갱신
        await interaction.response.edit_message(
            content=make_content_like_card(selected=sku),
            components=make_components_like_card()
        )
        return

    # 구매 버튼
    if cid == "shop:buy":
        sku = user_selected.get(interaction.user.id)
        if not sku:
            await interaction.response.send_message("먼저 상품을 선택해줘!", ephemeral=True)
            return
        try:
            await interaction.response.send_modal(QtyModal(sku))
        except discord.InteractionResponded:
            await interaction.followup.send("이미 처리 중이야. 다시 눌러줘!", ephemeral=True)
        return

    # 기타 버튼
    if cid == "shop:details":
        await interaction.response.send_message("자세한 가이드는 추후 연결 예정!", ephemeral=True)
        return

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 비었음. 넣어.")
    if CHANNEL_ID == 0:
        raise RuntimeError("CHANNEL_ID 비었음. 텍스트 채널 ID 넣어.")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
