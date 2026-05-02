from __future__ import annotations
import discord, asyncio
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from utils.db import GuildDB
from utils.helpers import is_guild_admin, is_registered, fmt, stars, log
from config import CHARGE_TIMEOUT_SEC

KST = timezone(timedelta(hours=9))


def _no_reg():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(discord.ui.TextDisplay("등록되지 않은 서버입니다."), accent_color=0xED4245)
    return V(timeout=None)

def _no_admin():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(discord.ui.TextDisplay("서버 관리자만 사용할 수 있습니다."), accent_color=0xED4245)
    return V(timeout=None)


# ─── 후기 ─────────────────────────────────────────────────────
class ReviewModal(discord.ui.Modal, title="후기 작성"):
    star    = discord.ui.TextInput(label="별점 (1~5)", min_length=1, max_length=1)
    content = discord.ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, max_length=500, required=False)

    def __init__(self, gid, uid, purchase_id, pname):
        super().__init__()
        self.gid = gid; self.uid = uid; self.purchase_id = purchase_id; self.pname = pname

    async def on_submit(self, i: discord.Interaction):
        try:
            s = int(self.star.value)
            if not 1 <= s <= 5: raise ValueError
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("별점은 1~5 숫자여야 합니다."), accent_color=0xED4245)
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
        GuildDB(self.gid).new_review(self.uid, self.purchase_id, s, self.content.value.strip())
        star_txt = stars(s)
        asyncio.create_task(log(self.gid, "review_log",
            f"후기 | 유저: <@{self.uid}> | 상품: {self.pname} | 별점: {star_txt}\n내용: {self.content.value or '(없음)'}"))
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(f"## 후기 등록 완료\n{star_txt}\n{self.pname}\n{self.content.value or ''}"),
                accent_color=0x57F287,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


class ReviewView(discord.ui.LayoutView):
    def __init__(self, gid, uid, purchase_id, pname, total):
        super().__init__(timeout=300)
        self.gid = gid; self.uid = uid; self.purchase_id = purchase_id
        self.pname = pname; self.total = total

    container = discord.ui.Container(
        discord.ui.TextDisplay("구매 완료! 후기를 남겨주세요."),
        accent_color=0x57F287,
    )
    row: discord.ui.ActionRow = discord.ui.ActionRow()

    @row.button(label="후기 작성", style=discord.ButtonStyle.secondary)
    async def write_review(self, i: discord.Interaction, btn: discord.ui.Button):
        if i.user.id != self.uid:
            await i.response.send_message("본인의 구매에만 후기를 쓸 수 있습니다.", ephemeral=True); return
        await i.response.send_modal(ReviewModal(self.gid, self.uid, self.purchase_id, self.pname))


# ─── 구매 ─────────────────────────────────────────────────────
class BuyQtyModal(discord.ui.Modal, title="구매 수량 입력"):
    qty = discord.ui.TextInput(label="수량", placeholder="1", max_length=4)

    def __init__(self, gid, uid, product):
        super().__init__(); self.gid = gid; self.uid = uid; self.product = product

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        try:
            q = int(self.qty.value.strip())
            if q < 1: raise ValueError
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("올바른 수량을 입력하세요."), accent_color=0xED4245)
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return

        gdb = GuildDB(self.gid); p = self.product
        user = gdb.get_user(self.uid)
        disc = user["discount_rate"]
        unit = int(p["price"] * (1 - disc / 100))
        total = unit * q

        if gdb.stock_cnt(p["id"]) < q:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 재고 부족\n상품: **{p['name']}**\n현재 재고: {gdb.stock_cnt(p['id'])}개 (요청: {q}개)"),
                    accent_color=0xED4245,
                )
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return

        if user["balance"] < total:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 잔액 부족\n필요: **{fmt(total)}**\n보유: **{fmt(user['balance'])}**"),
                    accent_color=0xED4245,
                )
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return

        items = gdb.pop_stock(p["id"], q)
        if not items:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("재고 처리 오류가 발생했습니다."), accent_color=0xED4245)
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return

        gdb.add_balance(self.uid, -total)
        gdb.add_spent(self.uid, total)
        purchase_id = gdb.new_purchase(self.uid, p["id"], p["name"], unit, q)

        await _grant_role(i, gdb, self.uid)

        dm_text = f"## 구매 완료 - {p['name']}\n수량: {q}개 | 합계: {fmt(total)}\n\n" + "\n".join(f"`{it}`" for it in items)
        dm_ok = True
        try: await i.user.send(dm_text)
        except discord.Forbidden: dm_ok = False

        upd = gdb.get_user(self.uid)
        asyncio.create_task(log(self.gid, "purchase_log",
            f"구매 | <@{self.uid}> | {p['name']} x{q} | {fmt(total)} | 잔액: {fmt(upd['balance'])}"))

        view = ReviewView(self.gid, self.uid, purchase_id, p["name"], total)
        for item in view.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                dm_note = "DM으로 제품이 전송되었습니다." if dm_ok else "DM 전송 실패 - DM 허용 후 다시 시도하세요."
                item.content = (
                    f"## 구매 완료\n상품: **{p['name']}**\n수량: **{q}개** | 합계: **{fmt(total)}**\n"
                    f"할인율: **{disc}%**\n{dm_note}"
                )
        await i.followup.send(view=view, ephemeral=True)


async def _grant_role(i: discord.Interaction, gdb: GuildDB, uid: int):
    member = i.guild.get_member(uid)
    if not member: return
    user = gdb.get_user(uid)
    for rc in sorted(gdb.get_roles(), key=lambda x: x["min_amount"], reverse=True):
        if user["total_spent"] >= rc["min_amount"] and rc["role_id"]:
            try:
                role = i.guild.get_role(int(rc["role_id"]))
                if role and role not in member.roles:
                    await member.add_roles(role, reason="자판기 누적 역할")
            except Exception: pass
            break


# ─── 구매 흐름 선택뷰 ─────────────────────────────────────────
class BuyProdView(discord.ui.LayoutView):
    def __init__(self, gid, uid, prods):
        super().__init__(timeout=60)
        self.gid = gid; self.uid = uid
        self._pmap = {str(p["id"]): p for p in prods}
        opts = [discord.SelectOption(label=f"{p['name']} | {fmt(p['price'])}", value=str(p["id"]),
                                     description=f"재고: {p['stock']}개") for p in prods[:25]]
        sel = discord.ui.Select(placeholder="상품을 선택하세요", options=opts)
        sel.callback = self._on_select
        self.add_item(discord.ui.ActionRow(sel))

    container = discord.ui.Container(
        discord.ui.TextDisplay("상품을 선택하세요."),
        accent_color=0x5865F2,
    )

    async def _on_select(self, i: discord.Interaction):
        p = self._pmap.get(i.data["values"][0])
        if not p:
            await i.response.send_message("상품을 찾을 수 없습니다.", ephemeral=True); return
        await i.response.send_modal(BuyQtyModal(self.gid, i.user.id, p))


class BuyCatView(discord.ui.LayoutView):
    def __init__(self, gid, cats):
        super().__init__(timeout=60)
        self.gid = gid
        opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in cats[:25]]
        sel = discord.ui.Select(placeholder="카테고리를 선택하세요", options=opts)
        sel.callback = self._on_select
        self.add_item(discord.ui.ActionRow(sel))

    container = discord.ui.Container(
        discord.ui.TextDisplay("카테고리를 선택하세요."),
        accent_color=0x5865F2,
    )

    async def _on_select(self, i: discord.Interaction):
        cid = int(i.data["values"][0])
        gdb = GuildDB(self.gid)
        prods = gdb.get_prods(cid)
        if not prods:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("이 카테고리에 상품이 없습니다."), accent_color=0xFEE75C)
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
        await i.response.send_message(view=BuyProdView(self.gid, i.user.id, prods), ephemeral=True)


# ─── 제품 보기 ────────────────────────────────────────────────
class BrowseView(discord.ui.LayoutView):
    def __init__(self, gid, cats):
        super().__init__(timeout=120)
        self.gid = gid; self._cats = {str(c["id"]): c["name"] for c in cats}
        opts = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in cats[:25]]
        sel = discord.ui.Select(placeholder="카테고리 선택", options=opts)
        sel.callback = self._on_select
        self.add_item(discord.ui.ActionRow(sel))

    container = discord.ui.Container(
        discord.ui.TextDisplay("카테고리를 선택하면 제품 목록이 표시됩니다."),
        accent_color=0x5865F2,
    )

    async def _on_select(self, i: discord.Interaction):
        cid = int(i.data["values"][0])
        gdb = GuildDB(self.gid)
        prods = gdb.get_prods(cid)
        cname = self._cats.get(str(cid), "")
        if not prods:
            txt = f"## {cname}\n상품이 없습니다."
        else:
            lines = [f"• {p['name']} | {fmt(p['price'])} | 재고: {p['stock']}개" for p in prods]
            txt = f"## {cname}\n" + "\n".join(lines)
        for item in self.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                item.content = txt
        await i.response.edit_message(view=self)


# ─── 충전 ─────────────────────────────────────────────────────
class ChargeModal(discord.ui.Modal, title="계좌이체 충전"):
    dep = discord.ui.TextInput(label="입금자명", placeholder="정확히 입력하세요")
    amt = discord.ui.TextInput(label="충전 금액 (원)", placeholder="10000")

    def __init__(self, gid, bot):
        super().__init__(); self.gid = gid; self.bot = bot

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        gdb = GuildDB(self.gid)
        bnum  = gdb.get_cfg("bank_num")
        bname = gdb.get_cfg("bank_name")
        bown  = gdb.get_cfg("bank_owner")
        mn    = int(gdb.get_cfg("min_charge", "0"))
        mx    = int(gdb.get_cfg("max_charge", "99999999"))
        if not bnum:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("충전 계좌가 설정되지 않았습니다."), accent_color=0xED4245)
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return
        try: amount = int(self.amt.value.replace(",",""))
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay("올바른 금액을 입력하세요."), accent_color=0xED4245)
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return
        if not mn <= amount <= mx:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay(f"충전 범위: {fmt(mn)} ~ {fmt(mx)}"), accent_color=0xED4245)
            await i.followup.send(view=Ve(timeout=None), ephemeral=True); return

        dep = self.dep.value.strip()
        charge_id = gdb.new_charge(i.user.id, amount, "transfer", dep)
        expire_t = (datetime.now(KST) + timedelta(seconds=CHARGE_TIMEOUT_SEC)).strftime("%H:%M")

        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 충전 신청 완료\n"
                    f"은행 : **{bname}**\n"
                    f"계좌 : **{bnum}**\n"
                    f"예금주 : **{bown}**\n"
                    f"금액 : **{fmt(amount)}**\n"
                    f"입금자명 : **{dep}**\n\n"
                    f"**{expire_t}** 까지 미입금시 자동 취소됩니다."
                ),
                accent_color=0x5865F2,
            )
        await i.followup.send(view=V(timeout=None), ephemeral=True)

        await asyncio.sleep(CHARGE_TIMEOUT_SEC)
        result = gdb.confirm_charge(charge_id)
        if result:  # 아직 pending → 취소
            gdb.cancel_charge(charge_id)


# ─── 내 정보 선택뷰 ───────────────────────────────────────────
class InfoHistSelect(discord.ui.Select):
    def __init__(self, gid, uid):
        self.gid = gid; self.uid = uid
        super().__init__(placeholder="내역 조회", options=[
            discord.SelectOption(label="최근 구매 내역", value="purchase"),
            discord.SelectOption(label="최근 충전 내역", value="charge"),
        ])
    async def callback(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        if self.values[0] == "purchase":
            recs = gdb.recent_purchases(self.uid)
            if not recs: txt = "## 최근 구매 내역\n내역이 없습니다."
            else:
                lines = [f"• {r['name']} x{r['qty']} | {fmt(r['price'])} | {r['date'][:10]}" for r in recs]
                txt = "## 최근 구매 내역\n" + "\n".join(lines)
        else:
            recs = gdb.recent_charges(self.uid)
            sm = {"pending":"대기","confirmed":"완료","cancelled":"취소"}
            if not recs: txt = "## 최근 충전 내역\n내역이 없습니다."
            else:
                lines = [f"• {fmt(r['amount'])} | {sm.get(r['status'],r['status'])} | {r['date'][:10]}" for r in recs]
                txt = "## 최근 충전 내역\n" + "\n".join(lines)
        for item in self.view.walk_children():
            if isinstance(item, discord.ui.TextDisplay):
                item.content = txt
        await i.response.edit_message(view=self.view)


class InfoView(discord.ui.LayoutView):
    def __init__(self, gid, uid, user_data):
        super().__init__(timeout=120)
        self.gid = gid; self.uid = uid
        ud = user_data
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 내 정보\n"
                f"잔액 : **{fmt(ud['balance'])}**\n"
                f"누적 구매 : **{fmt(ud['total_spent'])}**\n"
                f"할인율 : **{ud['discount_rate']}%**"
            ),
            accent_color=0x5865F2,
        )
        self.add_item(discord.ui.ActionRow(InfoHistSelect(gid, uid)))


# ─── 메인 자판기 뷰 ───────────────────────────────────────────
class VendingMainView(discord.ui.LayoutView):
    def __init__(self, gid, bot, title="자판기", desc="버튼을 눌러 이용하세요.", color=0x5865F2):
        super().__init__(timeout=None)
        self.gid = gid; self.bot = bot
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}\n{desc}"),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                discord.ui.Button(label="구매",      style=discord.ButtonStyle.success,   custom_id=f"v_buy_{gid}"),
                discord.ui.Button(label="제품 보기", style=discord.ButtonStyle.secondary, custom_id=f"v_browse_{gid}"),
                discord.ui.Button(label="충전",      style=discord.ButtonStyle.primary,   custom_id=f"v_charge_{gid}"),
                discord.ui.Button(label="내 정보",   style=discord.ButtonStyle.secondary, custom_id=f"v_info_{gid}"),
            ),
            accent_color=color,
        )

    async def interaction_check(self, i: discord.Interaction) -> bool:
        return True  # 누구나 사용

    async def on_interaction(self, i: discord.Interaction):
        cid = i.data.get("custom_id", "")
        gid = self.gid
        if cid == f"v_buy_{gid}":
            gdb = GuildDB(gid); cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
            await i.response.send_message(view=BuyCatView(gid, cats), ephemeral=True)

        elif cid == f"v_browse_{gid}":
            gdb = GuildDB(gid); cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
            await i.response.send_message(view=BrowseView(gid, cats), ephemeral=True)

        elif cid == f"v_charge_{gid}":
            gdb = GuildDB(gid)
            if not gdb.get_cfg("bank_num"):
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("충전 계좌가 설정되지 않았습니다."), accent_color=0xED4245)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True); return
            await i.response.send_modal(ChargeModal(gid, self.bot))

        elif cid == f"v_info_{gid}":
            gdb = GuildDB(gid)
            ud = gdb.get_user(i.user.id)
            await i.response.send_message(view=InfoView(gid, i.user.id, ud), ephemeral=True)


class VendingCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="자판기", description="자판기 메뉴 전송 (서버 관리자)")
    async def vending(self, i: discord.Interaction):
        if not is_registered(i.guild.id):
            await i.response.send_message(view=_no_reg(), ephemeral=True); return
        if not is_guild_admin(i.user):
            await i.response.send_message(view=_no_admin(), ephemeral=True); return

        gdb = GuildDB(i.guild.id)
        title = gdb.get_cfg("vending_title", "자판기")
        desc  = gdb.get_cfg("vending_desc",  "아래 버튼으로 이용하세요.")
        color_s = gdb.get_cfg("vending_color", "5865F2")
        try: color = int(color_s, 16)
        except Exception: color = 0x5865F2

        view = VendingMainView(i.guild.id, self.bot, title, desc, color)
        await i.response.send_message(view=view)
        msg = await i.original_response()
        gdb.save_vmsg(i.channel.id, msg.id)


async def setup(bot): await bot.add_cog(VendingCog(bot))
