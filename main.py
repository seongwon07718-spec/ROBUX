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


# ─── 모달들 ───────────────────────────────────────────────────
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


class AntiThirdModal(discord.ui.Modal, title="3자 방지 코드 설정"):
    code = discord.ui.TextInput(label="4자리 영숫자", min_length=4, max_length=4)

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        v = self.code.value.strip().upper()
        if not v.isalnum():
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("영숫자 4자리만 입력 가능합니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return
        GuildDB(self.gid).set_cfg("anti_third_code", v)
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(f"## 3자 방지 설정 완료\n코드 : `{v}`"), 
                accent_color=0x57F287
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


class LogModal(discord.ui.Modal, title="로그 채널 설정 (채널 ID)"):
    charge_ch   = discord.ui.TextInput(label="충전 로그 채널 ID",   required=False)
    purchase_ch = discord.ui.TextInput(label="구매 로그 채널 ID",   required=False)
    review_ch   = discord.ui.TextInput(label="후기 로그 채널 ID",   required=False)
    stock_ch    = discord.ui.TextInput(label="입고 로그 채널 ID",   required=False)
    admin_ch    = discord.ui.TextInput(label="관리자 로그 채널 ID", required=False)

    def __init__(self, gid, bot): 
        super().__init__(); self.gid = gid; self.bot = bot

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        gdb = GuildDB(self.gid)
        results = []
        pairs = [
            ("charge_log", self.charge_ch),
            ("purchase_log", self.purchase_ch),
            ("review_log", self.review_ch),
            ("stock_log", self.stock_ch),
            ("admin_log", self.admin_ch)
        ]
        for log_type, field in pairs:
            if not field.value.strip(): 
                continue
            try:
                ch = self.bot.get_channel(int(field.value.strip()))
                if ch and isinstance(ch, discord.TextChannel):
                    url = await make_webhook(ch, f"자판기_{log_type}")
                    if url:
                        gdb.set_wh(log_type, url)
                        results.append(f"#{ch.name} 설정 완료")
                    else:
                        results.append(f"#{ch.name} 웹훅 생성 실패")
                else:
                    results.append(f"채널 {field.value.strip()} 찾을 수 없음")
            except Exception as e:
                results.append(f"오류: {e}")
        
        txt = "\n".join(results) if results else "변경 없음"
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(f"## 로그 설정 완료\n{txt}"), 
                accent_color=0x57F287
            )
        await i.followup.send(view=V(timeout=None), ephemeral=True)


class CatAddModal(discord.ui.Modal, title="카테고리 추가"):
    name = discord.ui.TextInput(label="카테고리 이름", max_length=30)

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        ok = GuildDB(self.gid).add_cat(self.name.value.strip())
        txt = f"## 카테고리 추가 완료\n`{self.name.value.strip()}` 추가됨" if ok else f"## 중복 카테고리\n`{self.name.value.strip()}`는 이미 존재합니다."
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(txt), 
                accent_color=0x57F287 if ok else 0xED4245
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


class ProdAddModal(discord.ui.Modal, title="상품 추가"):
    cat_id = discord.ui.TextInput(label="카테고리 ID", placeholder="아래 목록 참조")
    name   = discord.ui.TextInput(label="상품 이름", max_length=50)
    price  = discord.ui.TextInput(label="가격 (원)")

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        try: 
            cid = int(self.cat_id.value)
            price = int(self.price.value.replace(",",""))
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("ID와 가격은 숫자여야 합니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        cats = {c["id"]: c["name"] for c in gdb.get_cats()}
        if cid not in cats:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("카테고리를 찾을 수 없습니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        pid = gdb.add_prod(cid, self.name.value.strip(), price)
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 상품 추가 완료\n[{pid}] {self.name.value.strip()} | {fmt(price)}\n카테고리: {cats[cid]}"
                ),
                accent_color=0x57F287,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


class StockModal(discord.ui.Modal, title="재고 추가"):
    pid   = discord.ui.TextInput(label="상품 ID")
    items = discord.ui.TextInput(label="재고 내용 (줄바꿈 구분)", style=discord.TextStyle.paragraph, max_length=4000)

    def __init__(self, gid): 
        super().__init__(); self.gid = gid

    async def on_submit(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        try: 
            pid = int(self.pid.value.strip())
        except ValueError:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("상품 ID는 숫자여야 합니다."), 
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

        added = gdb.add_stock(pid, self.items.value)
        total = gdb.stock_cnt(pid)

        import asyncio
        asyncio.create_task(log(self.gid, "stock_log",
            f"재고 입고 | 상품: {p['name']} | 추가: {added}개 | 총: {total}개"))

        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 재고 추가 완료\n상품: **{p['name']}**\n추가: **{added}개** | 총: **{total}개**"
                ),
                accent_color=0x57F287,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)


# ─── 기타 뷰들 ────────────────────────────────────────────────
class ChargeModeView(discord.ui.LayoutView):
    def __init__(self, gid: int):
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
        self._update_buttons()
        self.container[0].content = "## 자동 충전 활성화\n카카오뱅크 자동충전이 활성화됩니다."
        await i.response.edit_message(view=self)

    @row.button(label="수동 충전", style=discord.ButtonStyle.secondary)
    async def manual_btn(self, i: discord.Interaction, btn: discord.ui.Button):
        GuildDB(self.gid).set_cfg("charge_mode", "manual")
        self._update_buttons()
        self.container[0].content = "## 수동 충전 활성화\n관리자가 직접 충전을 확인합니다."
        await i.response.edit_message(view=self)

    def _update_buttons(self):
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                item.disabled = True


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


class CatDeleteView(discord.ui.LayoutView):
    def __init__(self, gid: int, cats: list):
        super().__init__(timeout=60)
        self.gid = gid
        options = [discord.SelectOption(label=c["name"], value=str(c["id"])) for c in cats[:25]]
        sel = discord.ui.Select(
            placeholder="삭제할 카테고리 선택", 
            options=options, 
            max_values=min(len(options), 5)
        )
        sel.callback = self._do_delete
        self.add_item(discord.ui.ActionRow(sel))

    container = discord.ui.Container(
        discord.ui.TextDisplay("삭제할 카테고리를 선택하세요."),
        discord.ui.Separator(),
        accent_color=0xFEE75C,
    )

    async def _do_delete(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        cats = {str(c["id"]): c["name"] for c in gdb.get_cats()}
        deleted = [cats.get(cid_s, cid_s) for cid_s in i.data["values"]]
        for cid_s in i.data["values"]:
            gdb.del_cat(int(cid_s))
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(f"## 카테고리 삭제 완료\n{', '.join(deleted)} 삭제됨"),
                accent_color=0x57F287,
            )
        await i.response.edit_message(view=V(timeout=None))


# ─── 메인 설정 ────────────────────────────────────────────────
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
        gdb = GuildDB(gid)

        if v == "role":
            await i.response.send_modal(RoleModal(gid))
        elif v == "basic":
            await i.response.send_modal(BasicModal(gid))
        elif v == "bank":
            await i.response.send_modal(BankModal(gid))
        elif v == "anti":
            await i.response.send_modal(AntiThirdModal(gid))
        elif v == "log":
            await i.response.send_modal(LogModal(gid, self.bot))
        elif v == "cat_add":
            await i.response.send_modal(CatAddModal(gid))
        elif v == "prod_add":
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("카테고리를 먼저 추가하세요."), 
                        accent_color=0xED4245
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            cat_txt = "\n".join(f"[{c['id']}] {c['name']}" for c in cats)
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 카테고리 목록\n{cat_txt}"), 
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send_modal(ProdAddModal(gid))

        elif v == "cat_list":
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("카테고리가 없습니다."), 
                        accent_color=0xFEE75C
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            cat_txt = "\n".join(f"[{c['id']}] {c['name']}" for c in cats)
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay(f"## 카테고리 목록\n{cat_txt}"), 
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send(view=CatDeleteView(gid, cats), ephemeral=True)

        elif v == "prod_list":
            cats = gdb.get_cats()
            if not cats:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("카테고리가 없습니다."), 
                        accent_color=0xFEE75C
                    )
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
            # 상품 삭제 버튼
            class DelView(discord.ui.LayoutView):
                row: discord.ui.ActionRow = discord.ui.ActionRow()
                @row.button(label="상품 삭제", style=discord.ButtonStyle.danger)
                async def del_btn(self2, ii: discord.Interaction, btn: discord.ui.Button):
                    await ii.response.send_modal(ProdDelModal(gid))
            await i.followup.send(view=DelView(timeout=60), ephemeral=True)

        elif v == "stock":
            prods = gdb.all_prods()
            if not prods:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay("상품이 없습니다."), 
                        accent_color=0xFEE75C
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            lines = [f"[{p['id']}] {p['cat_name']} > {p['name']} | 재고:{p['stock']}" for p in prods]
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("## 상품 목록\n" + "\n".join(lines)), 
                    accent_color=0x5865F2
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            await i.followup.send_modal(StockModal(gid))


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
