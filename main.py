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
    try: data = await req.json()
    except Exception: return web.json_response({"ok": False, "msg": "invalid json"}, status=400)

    server_id  = str(data.get("server_id",  "")).strip()
    license_k  = str(data.get("license",    "")).strip()
    ios_token  = str(data.get("ios_token",  "")).strip()
    kakao_msg  = str(data.get("kakao_msg",  "")).strip()

    if not all([server_id, license_k, ios_token, kakao_msg]):
        return web.json_response({"ok": False, "msg": "missing fields"}, status=400)

    try: gid = int(server_id)
    except ValueError: return web.json_response({"ok": False, "msg": "invalid server_id"}, status=400)

    # 라이센스 검증
    ldb = LicenseDB()
    lic = ldb.get_by_guild(gid)
    if not lic or lic["key_plain"] != license_k:
        return web.json_response({"ok": False, "msg": "invalid license"}, status=403)

    # iOS 토큰 검증
    gdb = GuildDB(gid)
    stored_token = gdb.get_cfg("ios_token")
    if not stored_token or stored_token != ios_token:
        return web.json_response({"ok": False, "msg": "invalid ios_token"}, status=403)

    # 자동충전 모드 확인
    if gdb.get_cfg("charge_mode", "manual") != "auto":
        return web.json_response({"ok": False, "msg": "auto charge disabled"}, status=403)

    # 카카오뱅크 메시지 파싱
    parsed = parse_kakao(kakao_msg)
    if not parsed:
        return web.json_response({"ok": False, "msg": "kakao parse failed"}, status=400)
    if parsed["type"] != "입금":
        return web.json_response({"ok": False, "msg": "not an incoming transaction"}, status=400)

    amount    = parsed["amount"]
    depositor = parsed["depositor"]

    if not depositor:
        return web.json_response({"ok": False, "msg": "depositor not found"}, status=400)

    # 금액 범위 확인
    mn = int(gdb.get_cfg("min_charge", "0"))
    mx = int(gdb.get_cfg("max_charge", "99999999"))
    if not mn <= amount <= mx:
        return web.json_response({"ok": False, "msg": f"amount out of range {mn}~{mx}"}, status=400)

    # pending 충전 매칭
    charge = gdb.pending_by_dep(depositor, amount)
    if not charge:
        return web.json_response({"ok": False, "msg": "no pending charge"}, status=404)

    confirmed = gdb.confirm_charge(charge["id"])
    if not confirmed:
        return web.json_response({"ok": False, "msg": "already processed"}, status=409)

    uid = int(confirmed["user_id"])
    gdb.add_balance(uid, amount)
    upd = gdb.get_user(uid)

    asyncio.create_task(log(gid, "charge_log",
        f"자동충전 완료 | <@{uid}> | 입금자: {depositor} | {fmt(amount)} | 잔액: {fmt(upd['balance'])}"))

    return web.json_response({"ok": True, "balance": upd["balance"]})


async def handle_health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


# ─── 수동충전 확인 뷰 ─────────────────────────────────────────
class ManualChargeView(discord.ui.LayoutView):
    def __init__(self, gid, charge_id, uid, amount):
        super().__init__(timeout=600)
        self.gid = gid; self.charge_id = charge_id; self.uid = uid; self.amount = amount

    container = discord.ui.Container(
        discord.ui.TextDisplay("충전을 처리하시겠습니까?"),
        accent_color=0x5865F2,
    )
    row: discord.ui.ActionRow = discord.ui.ActionRow()

    @row.button(label="충전 확인", style=discord.ButtonStyle.success)
    async def approve(self, i: discord.Interaction, btn: discord.ui.Button):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("관리자만 처리할 수 있습니다.", ephemeral=True); return
        gdb = GuildDB(self.gid)
        confirmed = gdb.confirm_charge(self.charge_id)
        if not confirmed:
            for item in self.walk_children():
                if isinstance(item, discord.ui.TextDisplay):
                    item.content = "이미 처리된 충전입니다."
            self._disable_all()
            await i.response.edit_message(view=self); return

        gdb.add_balance(self.uid, self.amount)
        upd = gdb.get_user(self.uid)
        try:
            member = await i.guild.fetch_member(self.uid)
            class Vdm(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 충전 완료\n{fmt(self.amount)} 충전되었습니다.\n현재 잔액: **{fmt(upd['balance'])}**"),
                    accent_color=0x57F287,
                )
            await member.send(view=Vdm(timeout=None))
        except Exception: pass

        for item in self.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                item.content = f"## 충전 처리 완료\n<@{self.uid}> | {fmt(self.amount)} | 잔액: {fmt(upd['balance'])}"
        self._disable_all()
        await i.response.edit_message(view=self)
        asyncio.create_task(log(self.gid, "charge_log",
            f"수동충전 완료 | 관리자: {i.user} | <@{self.uid}> | {fmt(self.amount)}"))

    @row.button(label="거절", style=discord.ButtonStyle.danger)
    async def reject(self, i: discord.Interaction, btn: discord.ui.Button):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("관리자만 처리할 수 있습니다.", ephemeral=True); return
        gdb = GuildDB(self.gid)
        gdb.cancel_charge(self.charge_id)
        try:
            member = await i.guild.fetch_member(self.uid)
            class Vdm(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("## 충전 거절\n충전 신청이 거절되었습니다."), accent_color=0xED4245)
            await member.send(view=Vdm(timeout=None))
        except Exception: pass
        for item in self.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                item.content = f"## 충전 거절됨\n<@{self.uid}> | {fmt(self.amount)}"
        self._disable_all()
        await i.response.edit_message(view=self)

    def _disable_all(self):
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button): item.disabled = True


class PendingSelect(discord.ui.Select):
    def __init__(self, gid, rows):
        self.gid = gid
        self._rmap = {str(r["id"]): r for r in rows}
        opts = [discord.SelectOption(
            label=f"[{r['id']}] {r['depositor'] or '?'} | {fmt(r['amount'])}",
            value=str(r["id"]),
            description=f"유저: {r['user_id']}"
        ) for r in rows[:25]]
        super().__init__(placeholder="처리할 충전 선택", options=opts)

    async def callback(self, i: discord.Interaction):
        row = self._rmap.get(self.values[0])
        if not row:
            await i.response.send_message("내역을 찾을 수 없습니다.", ephemeral=True); return
        view = ManualChargeView(self.gid, row["id"], int(row["user_id"]), row["amount"])
        for item in view.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                item.content = (
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
        lines = [f"[{r['id']}] <@{r['user_id']}> | {fmt(r['amount'])} | 입금자: {r['depositor'] or '?'} | {r['date'][:10]}"
                 for r in rows]
        self.container = discord.ui.Container(
            discord.ui.TextDisplay("## 수동 충전 대기 목록\n" + "\n".join(lines)),
            accent_color=0x5865F2,
        )
        self.add_item(discord.ui.ActionRow(PendingSelect(gid, rows)))


class WebhookChargeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post("/charge", handle_charge)
        self.app.router.add_get("/health",  handle_health)
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
                c = discord.ui.Container(discord.ui.TextDisplay("등록되지 않은 서버입니다."), accent_color=0xED4245)
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
        if not is_guild_admin(i.user):
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("관리자만 사용할 수 있습니다."), accent_color=0xED4245)
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return

        gdb = GuildDB(i.guild.id)
        rows = gdb.all_pending()
        if not rows:
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("## 수동 충전 대기 목록\n대기중인 충전이 없습니다."), accent_color=0x5865F2)
            await i.response.send_message(view=V(timeout=None), ephemeral=True); return

        await i.response.send_message(view=PendingListView(i.guild.id, rows), ephemeral=True)


async def setup(bot): await bot.add_cog(WebhookChargeCog(bot))
