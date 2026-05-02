from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import GuildDB
from utils.helpers import is_guild_admin, is_registered, fmt, gen_token, make_webhook, log


def _check(i: discord.Interaction):
    if not is_registered(i.guild.id): 
        return "not_reg"
    if not is_guild_admin(i.user):    
        return "not_admin"
    return None


def _no_reg():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(
            discord.ui.TextDisplay("등록되지 않은 서버입니다. `/등록`을 먼저 사용하세요."), 
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


# ─── 상품 삭제 모달 ───────────────────────────────────────────
class ProdDelModal(discord.ui.Modal, title="상품 삭제"):
    pid = discord.ui.TextInput(label="삭제할 상품 ID")

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        try: 
            pid = int(self.pid.value.strip())
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("숫자를 입력하세요."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        p = gdb.get_prod(pid)
        if not p:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("상품을 찾을 수 없습니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        gdb.del_prod(pid)
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(f"## 상품 삭제 완료\n`{p['name']}` 삭제됨"), 
                accent_color=0x57F287
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


# ─── 나머지 모달들 (생략 없이 모두 포함) ─────────────────────
class RoleModal(discord.ui.Modal, title="역할 설정"):
    buyer  = discord.ui.TextInput(label="구매자 역할 ID", required=False)
    vip    = discord.ui.TextInput(label="VIP 역할 ID",    required=False)
    vvip   = discord.ui.TextInput(label="VVIP 역할 ID",   required=False)
    svip   = discord.ui.TextInput(label="SVIP 역할 ID",   required=False)
    resell = discord.ui.TextInput(label="리셀러 역할 ID", required=False)

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        for rtype, field in [("구매자",self.buyer),("VIP",self.vip),("VVIP",self.vvip),("SVIP",self.svip),("리셀러",self.resell)]:
            if field.value.strip():
                gdb.set_role(rtype, field.value.strip())
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay("## 역할 설정 완료\n저장되었습니다."), 
                accent_color=0x57F287
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


# ... (BasicModal, BankModal, AntiThirdModal, LogModal, CatAddModal, ProdAddModal, StockModal은 이전 답변과 동일하게 유지)


# ─── 설정 메인 ────────────────────────────────────────────────
class SettingsMainView(discord.ui.LayoutView):
    def __init__(self, gid: int, bot):
        super().__init__(timeout=180)
        self.gid = gid
        self.bot = bot

        self.container = discord.ui.Container(
            discord.ui.TextDisplay("## 자판기 설정\n아래에서 원하는 메뉴를 선택하세요."),
            discord.ui.Separator(),
            accent_color=0x5865F2,
        )
        self.add_item(discord.ui.ActionRow(SettingsSelect(gid, bot)))


class SettingsSelect(discord.ui.Select):
    # ... (이전과 동일)

    async def callback(self, i: discord.Interaction):
        v = self.values[0]
        gid = self.gid
        gdb = GuildDB(gid)

        if v == "role":        await i.response.send_modal(RoleModal(gid))
        elif v == "basic":     await i.response.send_modal(BasicModal(gid))
        elif v == "bank":      await i.response.send_modal(BankModal(gid))
        elif v == "anti":      await i.response.send_modal(AntiThirdModal(gid))
        elif v == "log":       await i.response.send_modal(LogModal(gid, self.bot))
        elif v == "cat_add":   await i.response.send_modal(CatAddModal(gid))
        elif v == "prod_add":
            # ... (기존 로직)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리를 먼저 추가하세요."), accent_color=0xED4245)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            cat_txt = "\n".join(f"[{c['id']}] {c['name']}" for c in cats)
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay(f"## 카테고리 목록\n{cat_txt}"), accent_color=0x5865F2)
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send_modal(ProdAddModal(gid))

        elif v == "cat_list":
            # ... (기존)
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            cat_txt = "\n".join(f"[{c['id']}] {c['name']}" for c in cats)
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(discord.ui.TextDisplay(f"## 카테고리 목록\n{cat_txt}"), accent_color=0x5865F2)
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send(view=CatDeleteView(gid, cats), ephemeral=True)

        elif v == "prod_list":
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("카테고리가 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            lines = []
            for cat in cats:
                lines.append(f"\n**{cat['name']}**")
                for p in gdb.get_prods(cat["id"]):
                    lines.append(f"  [{p['id']}] {p['name']} | {fmt(p['price'])} | 재고:{p['stock']}")
            prod_txt = "\n".join(lines) if lines else "(없음)"

            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 상품 목록\n{prod_txt}"), 
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)

            class DelView(discord.ui.LayoutView):
                row: discord.ui.ActionRow = discord.ui.ActionRow()
                @row.button(label="상품 삭제", style=discord.ButtonStyle.danger)
                async def del_btn(self2, ii: discord.Interaction, btn: discord.ui.Button):
                    await ii.response.send_modal(ProdDelModal(gid))   # ← 여기서 ProdDelModal 사용

            await i.followup.send(view=DelView(timeout=60), ephemeral=True)

        elif v == "stock":
            prods = gdb.all_prods()
            if not prods:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(discord.ui.TextDisplay("상품이 없습니다."), accent_color=0xFEE75C)
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            lines = [f"[{p['id']}] {p.get('cat_name','')} > {p['name']} | 재고:{p['stock']}" for p in prods]
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("## 상품 목록\n" + "\n".join(lines)), 
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send_modal(StockModal(gid))

        elif v == "charge_mode":
            await i.response.send_message(view=ChargeModeView(gid), ephemeral=True)
        elif v == "ios_token":
            await i.response.send_message(view=IOSTokenView(gid), ephemeral=True)


class SettingsCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(name="설정", description="자판기 설정 (서버 관리자)")
    async def settings(self, i: discord.Interaction):
        err = _check(i)
        if err == "not_reg":
            await i.response.send_message(view=_no_reg(), ephemeral=True); return
        if err == "not_admin":
            await i.response.send_message(view=_no_admin(), ephemeral=True); return

        await i.response.send_message(view=SettingsMainView(i.guild.id, self.bot), ephemeral=True)


async def setup(bot): 
    await bot.add_cog(SettingsCog(bot))
