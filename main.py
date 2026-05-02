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

    server_id  = str(data.get("server_id", "")).strip()
    license_k  = str(data.get("license", "")).strip()
    ios_token  = str(data.get("ios_token", "")).strip()
    kakao_msg  = str(data.get("kakao_msg", "")).strip()

    if not all([server_id, license_k, ios_token, kakao_msg]):
        return web.json_response({"ok": False, "msg": "missing fields"}, status=400)

    try: gid = int(server_id)
    except ValueError: return web.json_response({"ok": False, "msg": "invalid server_id"}, status=400)

    ldb = LicenseDB()
    lic = ldb.get_by_guild(gid)
    if not lic or lic["key_plain"] != license_k:
        return web.json_response({"ok": False, "msg": "invalid license"}, status=403)

    gdb = GuildDB(gid)
    stored_token = gdb.get_cfg("ios_token")
    if not stored_token or stored_token != ios_token:
        return web.json_response({"ok": False, "msg": "invalid ios_token"}, status=403)

    if gdb.get_cfg("charge_mode", "manual") != "auto":
        return web.json_response({"ok": False, "msg": "auto charge disabled"}, status=403)

    parsed = parse_kakao(kakao_msg)
    if not parsed or parsed["type"] != "입금":
        return web.json_response({"ok": False, "msg": "invalid kakao message"}, status=400)

    amount = parsed["amount"]
    depositor = parsed["depositor"]

    if not depositor:
        return web.json_response({"ok": False, "msg": "depositor not found"}, status=400)

    mn = int(gdb.get_cfg("min_charge", "0"))
    mx = int(gdb.get_cfg("max_charge", "99999999"))
    if not mn <= amount <= mx:
        return web.json_response({"ok": False, "msg": f"amount out of range {mn}~{mx}"}, status=400)

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
    def __init__(self, gid: int, charge_id: int, uid: int, amount: int):
        super().__init__(timeout=600)
        self.gid = gid
        self.charge_id = charge_id
        self.uid = uid
        self.amount = amount

    # Container 안에 Text + Separator + ActionRow 모두 포함
    container = discord.ui.Container(
        discord.ui.TextDisplay("충전을 처리하시겠습니까?"),
        discord.ui.Separator(),
        # ActionRow를 Container 안에 직접 넣음
        discord.ui.ActionRow(
            discord.ui.Button(label="충전 확인", style=discord.ButtonStyle.success, custom_id="approve"),
            discord.ui.Button(label="거절", style=discord.ButtonStyle.danger, custom_id="reject"),
        ),
        accent_color=0x5865F2,
    )

    # 버튼 콜백은 on_interaction으로 처리
    async def on_interaction(self, i: discord.Interaction):
        if i.data.get("custom_id") == "approve":
            await self.approve(i)
        elif i.data.get("custom_id") == "reject":
            await self.reject(i)

    async def approve(self, i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("관리자만 처리할 수 있습니다.", ephemeral=True)
            return

        gdb = GuildDB(self.gid)
        confirmed = gdb.confirm_charge(self.charge_id)

        if not confirmed:
            self.container[0].content = "이미 처리된 충전입니다."
            self._disable_all()
            await i.response.edit_message(view=self)
            return

        gdb.add_balance(self.uid, self.amount)
        upd = gdb.get_user(self.uid)

        try:
            member = await i.guild.fetch_member(self.uid)
            class Vdm(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 충전 완료\n{fmt(self.amount)}원이 충전되었습니다.\n현재 잔액: **{fmt(upd['balance'])}**"),
                    accent_color=0x57F287,
                )
            await member.send(view=Vdm(timeout=None))
        except Exception:
            pass

        self.container[0].content = f"## 충전 처리 완료\n<@{self.uid}> | {fmt(self.amount)} | 잔액: {fmt(upd['balance'])}"
        self._disable_all()
        await i.response.edit_message(view=self)

        asyncio.create_task(log(self.gid, "charge_log",
            f"수동충전 완료 | 관리자: {i.user} | <@{self.uid}> | {fmt(self.amount)}"))

    async def reject(self, i: discord.Interaction):
        if not i.user.guild_permissions.administrator:
            await i.response.send_message("관리자만 처리할 수 있습니다.", ephemeral=True)
            return

        gdb = GuildDB(self.gid)
        gdb.cancel_charge(self.charge_id)

        try:
            member = await i.guild.fetch_member(self.uid)
            class Vdm(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("## 충전 거절\n충전 신청이 거절되었습니다."),
                    accent_color=0xED4245,
                )
            await member.send(view=Vdm(timeout=None))
        except Exception:
            pass

        self.container[0].content = f"## 충전 거절됨\n<@{self.uid}> | {fmt(self.amount)}"
        self._disable_all()
        await i.response.edit_message(view=self)

    def _disable_all(self):
        for child in self.container.children:
            if isinstance(child, discord.ui.ActionRow):
                for item in child.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True


# PendingSelect, PendingListView 등은 그대로 유지 (필요시 말씀해주세요)


class WebhookChargeCog(commands.Cog):
    # ... (기존과 동일)


async def setup(bot): 
    await bot.add_cog(WebhookChargeCog(bot))
