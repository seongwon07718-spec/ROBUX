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
        c = discord.ui.Container(
            discord.ui.TextDisplay("등록되지 않은 서버입니다."), 
            accent_color=0xED4245
        )
    return V(timeout=None)


def _no_admin():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(
            discord.ui.TextDisplay("서버 관리자만 사용할 수 있습니다."), 
            accent_color=0xED4245
        )
    return V(timeout=None)


# ─── 후기 ─────────────────────────────────────────────────────
class ReviewModal(discord.ui.Modal, title="후기 작성"):
    star = discord.ui.TextInput(label="별점 (1~5)", min_length=1, max_length=1)
    content = discord.ui.TextInput(
        label="후기 내용", 
        style=discord.TextStyle.paragraph, 
        max_length=500, 
        required=False
    )

    def __init__(self, gid, uid, purchase_id, pname):
        super().__init__()
        self.gid = gid
        self.uid = uid
        self.purchase_id = purchase_id
        self.pname = pname

    async def on_submit(self, i: discord.Interaction):
        try:
            s = int(self.star.value)
            if not 1 <= s <= 5:
                raise ValueError
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("별점은 1~5 숫자여야 합니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

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
    def __init__(self, gid, uid, purchase_id, pname):
        super().__init__(timeout=300)
        self.gid = gid
        self.uid = uid
        self.purchase_id = purchase_id
        self.pname = pname

    container = discord.ui.Container(
        discord.ui.TextDisplay("구매 완료! 후기를 남겨주세요."),
        discord.ui.Separator(),
        discord.ui.ActionRow(
            discord.ui.Button(label="후기 작성", style=discord.ButtonStyle.secondary, custom_id="write_review")
        ),
        accent_color=0x57F287,
    )

    async def on_interaction(self, i: discord.Interaction):
        if i.data.get("custom_id") == "write_review":
            if i.user.id != self.uid:
                await i.response.send_message("본인의 구매에만 후기를 쓸 수 있습니다.", ephemeral=True)
                return
            await i.response.send_modal(ReviewModal(self.gid, self.uid, self.purchase_id, self.pname))


# ─── 구매 ─────────────────────────────────────────────────────
class BuyQtyModal(discord.ui.Modal, title="구매 수량 입력"):
    qty = discord.ui.TextInput(label="수량", placeholder="1", max_length=4)

    def __init__(self, gid, uid, product):
        super().__init__()
        self.gid = gid
        self.uid = uid
        self.product = product

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        try:
            q = int(self.qty.value.strip())
            if q < 1: raise ValueError
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("올바른 수량을 입력하세요."), 
                    accent_color=0xED4245
                )
            await i.followup.send(view=Ve(timeout=None), ephemeral=True)
            return

        # ... (기존 로직 유지 - 생략) ...


# ─── 구매 흐름 선택뷰 ─────────────────────────────────────────
class BuyProdView(discord.ui.LayoutView):
    def __init__(self, gid, uid, prods):
        super().__init__(timeout=60)
        self.gid = gid
        self.uid = uid
        self._pmap = {str(p["id"]): p for p in prods}

        sel = discord.ui.Select(
            placeholder="상품을 선택하세요",
            options=[
                discord.SelectOption(
                    label=f"{p['name']} | {fmt(p['price'])}",
                    value=str(p["id"]),
                    description=f"재고: {p['stock']}개"
                ) for p in prods[:25]
            ]
        )
        sel.callback = self._on_select

        self.container = discord.ui.Container(
            discord.ui.TextDisplay("상품을 선택하세요."),
            discord.ui.Separator(),
            discord.ui.ActionRow(sel),          # ← Container 안에
            accent_color=0x5865F2,
        )

    async def _on_select(self, i: discord.Interaction):
        p = self._pmap.get(i.data["values"][0])
        if not p:
            await i.response.send_message("상품을 찾을 수 없습니다.", ephemeral=True)
            return
        await i.response.send_modal(BuyQtyModal(self.gid, i.user.id, p))


class BuyCatView(discord.ui.LayoutView):
    def __init__(self, gid, cats):
        super().__init__(timeout=60)
        self.gid = gid

        sel = discord.ui.Select(
            placeholder="카테고리를 선택하세요",
            options=[discord.SelectOption(label=c["name"], value=str(c["id"])) for c in cats[:25]]
        )
        sel.callback = self._on_select

        self.container = discord.ui.Container(
            discord.ui.TextDisplay("카테고리를 선택하세요."),
            discord.ui.Separator(),
            discord.ui.ActionRow(sel),
            accent_color=0x5865F2,
        )

    async def _on_select(self, i: discord.Interaction):
        cid = int(i.data["values"][0])
        gdb = GuildDB(self.gid)
        prods = gdb.get_prods(cid)
        if not prods:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("이 카테고리에 상품이 없습니다."), 
                    accent_color=0xFEE75C
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return
        await i.response.send_message(view=BuyProdView(self.gid, i.user.id, prods), ephemeral=True)


# ─── 제품 보기 ────────────────────────────────────────────────
class BrowseView(discord.ui.LayoutView):
    def __init__(self, gid, cats):
        super().__init__(timeout=120)
        self.gid = gid
        self._cats = {str(c["id"]): c["name"] for c in cats}

        sel = discord.ui.Select(
            placeholder="카테고리 선택",
            options=[discord.SelectOption(label=c["name"], value=str(c["id"])) for c in cats[:25]]
        )
        sel.callback = self._on_select

        self.container = discord.ui.Container(
            discord.ui.TextDisplay("카테고리를 선택하면 제품 목록이 표시됩니다."),
            discord.ui.Separator(),
            discord.ui.ActionRow(sel),
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

        self.container[0].content = txt
        await i.response.edit_message(view=self)


# ─── 충전 ─────────────────────────────────────────────────────
class ChargeModal(discord.ui.Modal, title="계좌이체 충전"):
    # ... (기존과 동일)


# ─── 내 정보 ──────────────────────────────────────────────────
class InfoHistSelect(discord.ui.Select):
    # ... (기존과 동일)

class InfoView(discord.ui.LayoutView):
    def __init__(self, gid, uid, user_data):
        super().__init__(timeout=120)
        self.gid = gid
        self.uid = uid

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 내 정보\n"
                f"잔액 : **{fmt(user_data['balance'])}**\n"
                f"누적 구매 : **{fmt(user_data['total_spent'])}**\n"
                f"할인율 : **{user_data['discount_rate']}%**"
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(InfoHistSelect(gid, uid)),
            accent_color=0x5865F2,
        )


# ─── 메인 자판기 뷰 ───────────────────────────────────────────
class VendingMainView(discord.ui.LayoutView):
    def __init__(self, gid, bot, title="자판기", desc="버튼을 눌러 이용하세요.", color=0x5865F2):
        super().__init__(timeout=None)
        self.gid = gid
        self.bot = bot

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

    async def on_interaction(self, i: discord.Interaction):
        cid = i.data.get("custom_id", "")
        
        if cid == f"v_buy_{self.gid}":
            gdb = GuildDB(self.gid)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_message(view=BuyCatView(self.gid, cats), ephemeral=True)

        elif cid == f"v_browse_{self.gid}":
            gdb = GuildDB(self.gid)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_message(view=BrowseView(self.gid, cats), ephemeral=True)

        elif cid == f"v_charge_{self.gid}":
            gdb = GuildDB(self.gid)
            if not gdb.get_cfg("bank_num"):
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("충전 계좌가 설정되지 않았습니다."), accent_color=0xED4245)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            await i.response.send_modal(ChargeModal(self.gid, self.bot))

        elif cid == f"v_info_{self.gid}":
            gdb = GuildDB(self.gid)
            ud = gdb.get_user(i.user.id)
            await i.response.send_message(view=InfoView(self.gid, i.user.id, ud), ephemeral=True)


class VendingCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(name="자판기", description="자판기 메뉴 전송 (서버 관리자)")
    async def vending(self, i: discord.Interaction):
        if not is_registered(i.guild.id):
            await i.response.send_message(view=_no_reg(), ephemeral=True)
            return
        if not is_guild_admin(i.user):
            await i.response.send_message(view=_no_admin(), ephemeral=True)
            return

        gdb = GuildDB(i.guild.id)
        title = gdb.get_cfg("vending_title", "자판기")
        desc  = gdb.get_cfg("vending_desc",  "아래 버튼으로 이용하세요.")
        color_s = gdb.get_cfg("vending_color", "5865F2")
        try: 
            color = int(color_s, 16)
        except Exception: 
            color = 0x5865F2

        view = VendingMainView(i.guild.id, self.bot, title, desc, color)
        await i.response.send_message(view=view)
        msg = await i.original_response()
        gdb.save_vmsg(i.channel.id, msg.id)


async def setup(bot): 
    await bot.add_cog(VendingCog(bot))
