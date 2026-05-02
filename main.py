from __future__ import annotations
import discord, io
from discord import app_commands
from discord.ext import commands
from utils.db import LicenseDB
from utils.helpers import is_bot_admin
from utils.ui import err_view
from config import LICENSE_PERIODS


def _not_admin():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(
            discord.ui.TextDisplay("봇 관리자만 사용할 수 있습니다."),
            accent_color=0xED4245,
        )
    return V(timeout=None)


class LicenseCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot
        self.db = LicenseDB()

    @app_commands.command(name="라이센스_생성", description="라이센스 생성 (봇 관리자)")
    @app_commands.describe(개수="발급할 개수", 기간="유효 기간")
    @app_commands.choices(기간=[app_commands.Choice(name=k, value=k) for k in LICENSE_PERIODS])
    async def create(self, i: discord.Interaction, 개수: int, 기간: str):
        if not is_bot_admin(i.user.id):
            await i.response.send_message(view=_not_admin(), ephemeral=True)
            return

        if not 1 <= 개수 <= 50:
            await i.response.send_message(view=err_view("개수는 1~50 사이여야 합니다."), ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        keys = self.db.create(개수, LICENSE_PERIODS[기간])
        txt = io.BytesIO("\n".join(keys).encode("utf-8"))
        
        filename = f"license_{기간}_{개수}ea.txt"
        file = discord.File(txt, filename=filename)

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 라이센스 생성 완료\n"
                    f"생성 수량 : **{개수}개**\n"
                    f"유효 기간 : **{기간}**\n"
                    f"키 목록 파일이 첨부되었습니다."
                ),
                discord.ui.File(f"attachment://{filename}"),   # ← V2 File Component
                accent_color=0x57F287,
            )

        await i.followup.send(
            view=V(timeout=None),
            files=[file],          # 실제 파일 업로드
            ephemeral=True
        )

    @app_commands.command(name="라이센스_삭제", description="라이센스 삭제 (봇 관리자)")
    @app_commands.describe(키="삭제할 키")
    async def delete(self, i: discord.Interaction, 키: str):
        if not is_bot_admin(i.user.id):
            await i.response.send_message(view=_not_admin(), ephemeral=True)
            return

        key = 키.strip()
        ok = self.db.delete(key)

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 라이센스 삭제 {'완료' if ok else '실패'}\n"
                    f"{'삭제된 키 : `' + key + '`' if ok else '해당 키를 찾을 수 없습니다 : `' + key + '`'}"
                ),
                accent_color=0x57F287 if ok else 0xED4245,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)

    @app_commands.command(name="라이센스_목록", description="라이센스 목록 조회 (봇 관리자 전용)")
    @app_commands.choices(상태=[
        app_commands.Choice(name="미사용 키", value="unused"),
        app_commands.Choice(name="사용중인 키", value="active"),
        app_commands.Choice(name="만료된 키", value="expired"),
        app_commands.Choice(name="전체", value="all"),
    ])
    async def list_lic(self, i: discord.Interaction, 상태: str):
        if not is_bot_admin(i.user.id):
            await i.response.send_message(view=_not_admin(), ephemeral=True)
            return

        await i.response.defer(ephemeral=True)

        recs = self.db.get_all(None if 상태 == "all" else 상태)
        sm = {"unused":"미사용", "active":"사용중", "expired":"만료"}
        
        lines = [
            f"[{sm.get(r['status'], r['status'])}] {r['key_plain']} | {r['period_days']}일 | "
            f"만료:{(r.get('expires_at') or '-')[:10]}"
            + (f" | 서버:{r['guild_id']}" if r.get('guild_id') else "")
            for r in recs
        ]

        filename = f"license_{상태}.txt"
        file = discord.File(
            io.BytesIO(("\n".join(lines) or "없음").encode("utf-8")),
            filename=filename
        )

        lmap = {"unused":"미사용", "active":"사용중", "expired":"만료", "all":"전체"}

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 라이센스 목록 ({lmap.get(상태, 상태)})\n"
                    f"총 **{len(recs)}개** 조회\n"
                    f"파일이 첨부되었습니다."
                ),
                discord.ui.File(f"attachment://{filename}"),   # ← V2 File Component
                accent_color=0x5865F2,
            )

        await i.followup.send(
            view=V(timeout=None),
            files=[file],
            ephemeral=True
        )


async def setup(bot): 
    await bot.add_cog(LicenseCog(bot))
