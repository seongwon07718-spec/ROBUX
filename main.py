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


# ─── 모달들 (기존 로직 유지) ─────────────────────────────────────
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


class BasicModal(discord.ui.Modal, title="기본 설정"):
    title_t = discord.ui.TextInput(label="자판기 제목", required=False)
    desc_t  = discord.ui.TextInput(label="설명", style=discord.TextStyle.paragraph, required=False, max_length=500)
    image   = discord.ui.TextInput(label="이미지 URL", required=False)
    color   = discord.ui.TextInput(label="색상 Hex (예: #5865F2)", required=False)

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        if self.title_t.value: gdb.set_cfg("vending_title", self.title_t.value)
        if self.desc_t.value:  gdb.set_cfg("vending_desc",  self.desc_t.value)
        if self.image.value:   gdb.set_cfg("vending_image", self.image.value)
        if self.color.value:   gdb.set_cfg("vending_color", self.color.value.lstrip("#"))
        
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay("## 기본 설정 완료"), 
                accent_color=0x57F287
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


class BankModal(discord.ui.Modal, title="충전 계좌 설정"):
    bnum  = discord.ui.TextInput(label="계좌번호")
    bname = discord.ui.TextInput(label="은행명")
    owner = discord.ui.TextInput(label="예금주")
    bmin  = discord.ui.TextInput(label="최소 충전 금액")
    bmax  = discord.ui.TextInput(label="최대 충전 금액")

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        try:
            mn = int(self.bmin.value.replace(",",""))
            mx = int(self.bmax.value.replace(",",""))
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("금액은 숫자여야 합니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        gdb = GuildDB(self.gid)
        gdb.set_cfg("bank_num",   self.bnum.value.strip())
        gdb.set_cfg("bank_name",  self.bname.value.strip())
        gdb.set_cfg("bank_owner", self.owner.value.strip())
        gdb.set_cfg("min_charge", str(mn))
        gdb.set_cfg("max_charge", str(mx))

        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 계좌 설정 완료\n{self.bname.value} | {self.bnum.value}\n"
                    f"예금주: {self.owner.value}\n충전 범위: {fmt(mn)} ~ {fmt(mx)}"
                ),
                accent_color=0x57F287,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


# (AntiThirdModal, LogModal, CatAddModal, ProdAddModal, StockModal 등은 기존 로직 유지 - 필요시 말씀해주세요)


# ─── 충전 방식 선택 ───────────────────────────────────────────
class ChargeModeView(discord.ui.LayoutView):
    def __init__(self, gid: int, current: str):
        super().__init__(timeout=60)
        self.gid = gid

    container = discord.ui.Container(
        discord.ui.TextDisplay("충전 방식을 선택하세요."),
        discord.ui.Separator(),
        accent_color=0x5865F2,
    )

    row: discord.ui.ActionRow = discord.ui.ActionRow()

    @row.button(label="자동 충전", style=discord.ButtonStyle.primary)
    async def auto_btn(self, i: discord.Interaction, btn: discord.ui.Button):
        GuildDB(self.gid).set_cfg("charge_mode", "auto")
        self._update_buttons(btn)
        self.container[0].content = "## 자동 충전 활성화\n카카오뱅크 자동충전이 활성화됩니다."
        await i.response.edit_message(view=self)

    @row.button(label="수동 충전", style=discord.ButtonStyle.secondary)
    async def manual_btn(self, i: discord.Interaction, btn: discord.ui.Button):
        GuildDB(self.gid).set_cfg("charge_mode", "manual")
        self._update_buttons(btn)
        self.container[0].content = "## 수동 충전 활성화\n관리자가 직접 충전을 확인합니다."
        await i.response.edit_message(view=self)

    def _update_buttons(self, clicked_btn):
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                item.disabled = True


# ─── iOS 토큰 발급 ────────────────────────────────────────────
class IOSTokenView(discord.ui.LayoutView):
    def __init__(self, gid: int):
        super().__init__(timeout=60)
        self.gid = gid

    container = discord.ui.Container(
        discord.ui.TextDisplay("iOS 자동충전 토큰을 발급합니다.\n서버당 **1회**만 발급됩니다."),
        discord.ui.Separator(),
        accent_color=0x5865F2,
    )

    row: discord.ui.ActionRow = discord.ui.ActionRow()

    @row.button(label="토큰 발급", style=discord.ButtonStyle.success)
    async def issue(self, i: discord.Interaction, btn: discord.ui.Button):
        gdb = GuildDB(self.gid)
        existing = gdb.get_cfg("ios_token")
        if existing:
            self.container[0].content = f"## 이미 발급된 토큰\n||`{existing}`||\n서버당 1회만 발급 가능합니다."
            btn.disabled = True
            await i.response.edit_message(view=self)
            return

        token = gen_token()
        gdb.set_cfg("ios_token", token)
        btn.disabled = True
        self.container[0].content = f"## iOS 토큰 발급 완료\n||`{token}`||\n이 토큰을 안전하게 보관하세요."
        await i.response.edit_message(view=self)


# ─── 메인 설정 뷰 ─────────────────────────────────────────────
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
    def __init__(self, gid: int, bot):
        self.gid = gid
        self.bot = bot
        super().__init__(
            placeholder="설정 항목 선택",
            options=[
                discord.SelectOption(label="역할 설정",          value="role"),
                discord.SelectOption(label="기본 설정",          value="basic"),
                discord.SelectOption(label="충전 계좌 설정",     value="bank"),
                discord.SelectOption(label="카테고리 추가",      value="cat_add"),
                discord.SelectOption(label="카테고리 목록/삭제", value="cat_list"),
                discord.SelectOption(label="상품 추가",          value="prod_add"),
                discord.SelectOption(label="상품 목록/삭제",     value="prod_list"),
                discord.SelectOption(label="재고 설정",          value="stock"),
                discord.SelectOption(label="3자 방지 설정",      value="anti"),
                discord.SelectOption(label="자충/수충 설정",     value="charge_mode"),
                discord.SelectOption(label="iOS 자충 토큰 발급", value="ios_token"),
                discord.SelectOption(label="로그 설정",          value="log"),
            ]
        )

    async def callback(self, i: discord.Interaction):
        v = self.values[0]
        gid = self.gid

        if v == "role":        await i.response.send_modal(RoleModal(gid))
        elif v == "basic":     await i.response.send_modal(BasicModal(gid))
        elif v == "bank":      await i.response.send_modal(BankModal(gid))
        elif v == "anti":      await i.response.send_modal(AntiThirdModal(gid))
        elif v == "log":       await i.response.send_modal(LogModal(gid, self.bot))
        elif v == "cat_add":   await i.response.send_modal(CatAddModal(gid))
        elif v == "charge_mode":
            current = GuildDB(gid).get_cfg("charge_mode", "manual")
            await i.response.send_message(view=ChargeModeView(gid, current), ephemeral=True)
        elif v == "ios_token":
            await i.response.send_message(view=IOSTokenView(gid), ephemeral=True)
        # ... (cat_list, prod_list, stock, prod_add 등은 기존 로직 유지)


class SettingsCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(name="설정", description="자판기 설정 (서버 관리자)")
    async def settings(self, i: discord.Interaction):
        err = _check(i)
        if err == "not_reg":
            await i.response.send_message(view=_no_reg(), ephemeral=True)
            return
        if err == "not_admin":
            await i.response.send_message(view=_no_admin(), ephemeral=True)
            return

        await i.response.send_message(
            view=SettingsMainView(i.guild.id, self.bot), 
            ephemeral=True
        )


async def setup(bot): 
    await bot.add_cog(SettingsCog(bot))
