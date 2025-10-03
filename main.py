import os
import aiohttp
import asyncio
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

GUILD_ID = 1419200424636055592  # 네 길드

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 카드 v2 페이로드 (임베드 사용 안 함)
def make_card_message():
    return {
        "content": "",
        "components": [
            {
                "type": "card",      # 카드 컨테이너 (v2 스타일)
                "children": [
                    {
                        "type": "card_header",
                        "title": "상점 카드",
                        "subtitle": "로벅스 상품 안내"
                    },
                    {
                        "type": "section",
                        "text": "상품을 고르고 아래 버튼으로 구매 진행해줘."
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
        ],
        "allowed_mentions": {"parse": []}
    }

# 안전 가드: 채널 검증 (존재/길드 일치/권한)
async def validate_channel(bot: commands.Bot, channel_id: int) -> tuple[bool, str]:
    ch = bot.get_channel(channel_id)
    if ch is None:
        # 캐시에 없을 수 있으니 API 조회
        try:
            ch = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            return False, "채널이 존재하지 않음 (NotFound). CHANNEL_ID 다시 확인."
        except discord.Forbidden:
            return False, "채널 정보를 볼 권한이 없음 (Forbidden). 봇 권한 확인."
        except discord.HTTPException as e:
            return False, f"채널 조회 실패(HTTPException): {e}"

    # 텍스트 채널인지 체크
    if not isinstance(ch, (discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel)):
        # 카드 전송은 텍스트 메시지가 가능한 곳이어야 함
        if not isinstance(ch, discord.TextChannel):
            return False, "텍스트 채널이 아님. 일반 텍스트 채널 ID를 넣어줘."

    # 길드 일치 체크
    if getattr(ch, "guild", None) and ch.guild.id != GUILD_ID:
        return False, f"길드 불일치. 채널의 길드({ch.guild.id}) != 기대 길드({GUILD_ID})."

    # 권한 체크
    perms = ch.permissions_for(ch.guild.me) if getattr(ch, "guild", None) else None
    if perms and not perms.send_messages:
        return False, "메시지 보내기 권한 없음. 채널 권한 부여 필요."
    return True, "OK"

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
    print(f"READY {bot.user} | guild={GUILD_ID} | channel={CHANNEL_ID}")

    # 길드 캐시 확인
    g = bot.get_guild(GUILD_ID)
    if g is None:
        print("경고: 봇이 해당 길드 캐시에 없음. 초대/권한/Shard 범위 확인.")

    # 채널 검증
    ok, reason = await validate_channel(bot, CHANNEL_ID)
    if not ok:
        print(f"[차단] 카드 전송 중단: {reason}")
        return
    print("[검증 통과] 채널로 카드 전송 시도")

    # 원시 HTTP로 카드 전송
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}
    payload = make_card_message()

    async with aiohttp.ClientSession(headers=headers) as s:
        async with s.post(url, json=payload) as r:
            body = await r.text()
            print("send card:", r.status, body)
            if r.status == 404:
                print("Unknown Channel 10003: 채널 ID 틀림 or 봇 권한/길드 불일치. 위 검증 메시지 참고해서 수정해.")
            elif r.status >= 300:
                print("전송 실패. 위 HTTP 응답 본문(body) 확인하고 키/권한/롤아웃 점검.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    data = getattr(interaction, "data", {}) or {}
    cid = data.get("custom_id")
    if not cid:
        return
    if cid.startswith("shop:buy:"):
        sku = cid.split(":")[-1]
        try:
            await interaction.response.send_modal(QtyModal(sku))
        except discord.InteractionResponded:
            await interaction.followup.send("이미 처리된 인터랙션이야. 다시 눌러줘!", ephemeral=True)

def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 비어있음. 환경변수 넣어.")
    if CHANNEL_ID == 0:
        raise RuntimeError("CHANNEL_ID 비어있음. 텍스트 채널 ID 넣어.")
    # 슬래시 커맨드 일절 안 씀 → 'shop not found' 재발 불가
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
