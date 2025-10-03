import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
GUILD_ID = 1419200424636055592  # 네 서버 ID 박제

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 채널 검증: 존재/길드 일치/권한 체크
async def validate_channel(bot: commands.Bot, channel_id: int) -> tuple[bool, str]:
    ch = bot.get_channel(channel_id)
    if ch is None:
        try:
            ch = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            return False, "채널이 존재하지 않음. CHANNEL_ID 다시 확인."
        except discord.Forbidden:
            return False, "채널 조회 권한 없음. 봇 권한 확인."
        except discord.HTTPException as e:
            return False, f"채널 조회 실패: {e}"
    if not isinstance(ch, discord.TextChannel):
        return False, "텍스트 채널 ID가 아님. 일반 텍스트 채널 ID 넣어."
    if ch.guild.id != GUILD_ID:
        return False, f"길드 불일치: 채널 길드({ch.guild.id}) != 기대 길드({GUILD_ID})"
    perms = ch.permissions_for(ch.guild.me)
    if not perms.send_messages:
        return False, "메시지 보내기 권한 없음. 채널 권한 부여 필요."
    return True, "OK"

# 카드 느낌의 본문(임베드 X)
def make_content_like_card(selected=None):
    top = (
        "┌─────────────────────────────────\n"
        "│ 테스트입니다.\n"
        "│ Python으로 Components V2 느낌 살려서 사용.\n"
        "│ Discord.py로 인터랙션 처리.\n"
        "└─────────────────────────────────"
    )
    if selected:
        top += f"\n선택한 상품: {selected}"
    return top

# 호환 컴포넌트(숫자 타입만) – REST에서 100% 통과
def make_components_like_card():
    return [
        {
            "type": 1,  # Action Row
            "components": [
                {
                    "type": 3,  # String Select
                    "custom_id": "shop:select",
                    "placeholder": "상품을 선택해줘",
                    "min_values": 1,
                    "max_values": 1,
                    "options": [
                        {"label": "Robux 100", "value": "rbx100", "description": "100 크레딧"},
                        {"label": "Robux 500", "value": "rbx500", "description": "500 크레딧"},
                        {"label": "Robux 1000", "value": "rbx1k", "description": "1000 크레딧"},
                    ],
                }
            ],
        },
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 3, "label": "구매", "custom_id": "shop:buy"},
                {"type": 2, "style": 2, "label": "자세히", "custom_id": "shop:details"},
            ],
        },
    ]

# 유저별 선택값 간단 캐시
user_selected = {}

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
            await interaction.response.send_message("수량이 올바르지 않아. 1 이상 정수로!", ephemeral=True)
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
                print("전송 실패. 위 body 확인해서 길이/권한 점검.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    data = getattr(interaction, "data", {}) or {}
    cid = data.get("custom_id")

    # 셀렉트 선택
    if cid == "shop:select":
        values = data.get("values") or []
        sku = values[0] if values else None
        if not sku:
            await interaction.response.send_message("선택값 없음. 다시 시도!", ephemeral=True)
            return
        user_selected[interaction.user.id] = sku
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
            await interaction.followup.send("이미 처리 중. 다시 눌러줘!", ephemeral=True)
        return

    # 자세히 버튼
    if cid == "shop:details":
        await interaction.response.send_message("자세한 가이드는 곧 연결!", ephemeral=True)
        return

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 비어있음.")
    if CHANNEL_ID == 0:
        raise RuntimeError("CHANNEL_ID 비어있음. 텍스트 채널 ID 필요.")
    # 슬래시/트리 호출 일절 없음 → 'shop not found' 재발 불가
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
