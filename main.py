from __future__ import annotations
import discord, asyncio, logging
from discord import app_commands
from discord.ext import commands
from aiohttp import web
from utils.db import LicenseDB, GuildDB
from utils.helpers import log, fmt, parse_kakao
from config import WEBHOOK_HOST, WEBHOOK_PORT

logger = logging.getLogger("vending_bot.wh")


# ─── iOS 자동충전 엔드포인트 ──────────────────────────────────
async def handle_charge(req: web.Request) -> web.Response:
    # ... (기존 코드 그대로 유지)
    # (생략)


async def handle_health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


# ─── 수동충전 확인 뷰 ─────────────────────────────────────────
class ManualChargeView(discord.ui.LayoutView):
    def __init__(self, gid: int, charge_id: int, uid: int, amount: int):
        super().__init__(timeout=600)
        self.gid = gid
        self.charge_id = charge_id
        self.uid = uid
        self.amount = amount

    container = discord.ui.Container(
        discord.ui.TextDisplay("충전을 처리하시겠습니까?"),
        discord.ui.Separator(),
        discord.ui.ActionRow(
            discord.ui.Button(label="충전 확인", style=discord.ButtonStyle.success, custom_id="approve"),
            discord.ui.Button(label="거절", style=discord.ButtonStyle.danger, custom_id="reject"),
        ),
        accent_color=0x5865F2,
    )

    async def on_interaction(self, i: discord.Interaction):
        if i.data.get("custom_id") == "approve":
            await self.approve(i)
        elif i.data.get("custom_id") == "reject":
            await self.reject(i)

    # approve, reject 메서드는 이전과 동일 (생략 가능)


# ─── 대기 목록 Select + View ───────────────────────────────────
class PendingSelect(discord.ui.Select):
    def __init__(self, gid, rows):
        self.gid = gid
        self._rmap = {str(r["id"]): r for r in rows}
        opts = [
            discord.SelectOption(
                label=f"[{r['id']}] {r['depositor'] or '?'} | {fmt(r['amount'])}",
                value=str(r["id"]),
                description=f"유저: {r['user_id']}"
            ) for r in rows[:25]
        ]
        super().__init__(placeholder="처리할 충전 선택", options=opts)

    async def callback(self, i: discord.Interaction):
        row = self._rmap.get(self.values[0])
        if not row:
            await i.response.send_message("내역을 찾을 수 없습니다.", ephemeral=True)
            return

        view = ManualChargeView(self.gid, row["id"], int(row["user_id"]), row["amount"])
        view.container[0].content = (
            f"## 충전 처리\n"
            f"유저 : <@{row['user_id']}>\n"
            f"금액 : **{fmt(row['amount'])}**\n"
            f"입금자 : **{row['depositor'] or '?'}**\n"
            f"신청일 : {row['date'][:10]}"
        )
        await i.response.send_message(view=view, ephemeral=True)


class PendingListView(discord.ui.LayoutView):
    def __init__(self, gid, rows):
        super().__init__(timeout=120)
        self.gid = gid

        lines = [
            f"[{r['id']}] <@{r['user_id']}> | {fmt(r['amount'])} | 입금자: {r['depositor'] or '?'} | {r['date'][:10]}"
            for r in rows
        ]

        # Container 안에 Select도 함께 배치
        self.container = discord.ui.Container(
            discord.ui.TextDisplay("## 수동 충전 대기 목록\n" + "\n".join(lines)),
            discord.ui.Separator(),
            discord.ui.ActionRow(PendingSelect(gid, rows)),   # ← Select를 Container 안에
            accent_color=0x5865F2,
        )


class WebhookChargeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post("/charge", handle_charge)
        self.app.router.add_get("/health", handle_health)
        self.runner = None
        bot.loop.create_task(self._start())

    async def _start(self):
        await self.bot.wait_until_ready()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, WEBHOOK_HOST, WEBHOOK_PORT)
        await site.start()
        logger.info(f"자동충전 서버: {WEBHOOK_HOST}:{WEBHOOK_PORT}")

    def cog_unload(self):
        if self.runner:
            asyncio.create_task(self.runner.cleanup())

    @app_commands.command(name="충전확인", description="충전 대기 유저 확인 (서버 관리자)")
    async def charge_confirm(self, i: discord.Interaction):
        from utils.helpers import is_registered, is_guild_admin
        if not is_registered(i.guild.id):
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("등록되지 않은 서버입니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        if not is_guild_admin(i.user):
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("관리자만 사용할 수 있습니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        gdb = GuildDB(i.guild.id)
        rows = gdb.all_pending()

        if not rows:
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("## 수동 충전 대기 목록\n대기중인 충전이 없습니다."),
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            return

        await i.response.send_message(view=PendingListView(i.guild.id, rows), ephemeral=True)


async def setup(bot): 
    await bot.add_cog(WebhookChargeCog(bot))
