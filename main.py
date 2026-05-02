from __future__ import annotations
import discord, os
from discord import app_commands
from discord.ext import commands, tasks
from pathlib import Path
from utils.db import LicenseDB, ServerListDB, GuildDB
from utils.helpers import is_registered


def _already_registered(exp: str):
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(
            discord.ui.TextDisplay(f"## 이미 등록된 서버\n만료일 : **{exp}**"),
            accent_color=0xFEE75C,
        )
    return V(timeout=None)


# ─── 라이센스 등록 모달 ───────────────────────────────────────
class LicenseModal(discord.ui.Modal, title="라이센스 등록"):
    key = discord.ui.TextInput(
        label="라이센스 키", 
        placeholder="지급 받은 라이센스 키를 입력해주세요.", 
        min_length=15, 
        max_length=20
    )

    def __init__(self, bot): 
        super().__init__(); self.bot = bot

    async def on_submit(self, i: discord.Interaction):
        k = self.key.value.strip()
        ldb = LicenseDB()
        row = ldb.c.execute(
            "SELECT * FROM licenses WHERE key_plain=? AND status='unused'", 
            (k,)
        ).fetchone()

        if not row:
            class V(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("유효하지 않은 키이거나 이미 사용된 키입니다."),
                    accent_color=0xED4245,
                )
            await i.response.send_message(view=V(timeout=None), ephemeral=True)
            return

        from utils.db import _cols
        data = dict(zip(_cols(ldb.c, "licenses"), row))

        view = ConfirmView(self.bot, k, data["period_days"], i.guild)
        await i.response.send_message(view=view, ephemeral=True)


# ─── 등록 확인 뷰 ─────────────────────────────────────────────
class ConfirmView(discord.ui.LayoutView):
    def __init__(self, bot, key: str, period_days: int, guild: discord.Guild):
        super().__init__(timeout=60)
        self.bot = bot
        self.key = key
        self.period_days = period_days
        self.guild = guild

    container = discord.ui.Container(
        discord.ui.TextDisplay("등록을 진행하시겠습니까?"),
        discord.ui.Separator(),
        # 버튼들을 Container 안에 직접 배치
        discord.ui.ActionRow(
            discord.ui.Button(label="등록 진행", style=discord.ButtonStyle.success, custom_id="confirm"),
            discord.ui.Button(label="등록 취소", style=discord.ButtonStyle.danger, custom_id="cancel"),
        ),
        accent_color=0x5865F2,
    )

    async def on_interaction(self, i: discord.Interaction):
        if i.data.get("custom_id") == "confirm":
            await self.confirm(i)
        elif i.data.get("custom_id") == "cancel":
            await self.cancel(i)

    async def confirm(self, i: discord.Interaction):
        ldb = LicenseDB()
        result = ldb.activate(self.key, self.guild.id)

        if not result:
            self.container[0].content = "이미 사용된 키입니다."
            self.container.accent_color = 0xED4245
            self._disable_all()
            await i.response.edit_message(view=self)
            return

        # GuildDB 초기화 + ServerListDB 등록
        gdb = GuildDB(self.guild.id)
        sldb = ServerListDB()
        sldb.upsert(
            self.guild.id, 
            self.guild.name, 
            "active", 
            result["expires_at"], 
            self.key
        )

        exp = result["expires_at"][:10]

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 서비스 등록 완료\n"
                    f"서버 : **{self.guild.name}**\n"
                    f"만료일 : **{exp}**\n\n"
                    f"`/설정` 명령어로 자판기를 설정해주세요."
                ),
                accent_color=0x57F287,
            )
        await i.response.edit_message(view=V(timeout=None))

    async def cancel(self, i: discord.Interaction):
        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay("등록이 취소되었습니다."), 
                accent_color=0xED4245
            )
        await i.response.edit_message(view=V(timeout=None))

    def _disable_all(self):
        for child in self.container.children:
            if isinstance(child, discord.ui.ActionRow):
                for item in child.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True


class RegistrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.expire_task.start()

    def cog_unload(self):
        self.expire_task.cancel()

    @app_commands.command(name="등록", description="자판기 서비스를 등록합니다 (라이센스 필요)")
    async def register(self, i: discord.Interaction):
        if is_registered(i.guild.id):
            ldb = LicenseDB()
            lic = ldb.get_by_guild(i.guild.id)
            exp = (lic["expires_at"] or "")[:10] if lic else "알 수 없음"
            await i.response.send_message(
                view=_already_registered(exp), 
                ephemeral=True
            )
            return

        await i.response.send_modal(LicenseModal(self.bot))

    @tasks.loop(minutes=10)
    async def expire_task(self):
        ldb = LicenseDB()
        sldb = ServerListDB()
        for gid_str in ldb.expire_check():
            try:
                gid = int(gid_str)
                sldb.set_expired(gid)
                db_path = Path(f"SERVER/{gid}.db")
                if db_path.exists():
                    os.remove(db_path)
            except Exception:
                pass

    @expire_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()


async def setup(bot): 
    await bot.add_cog(RegistrationCog(bot))
