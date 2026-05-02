from __future__ import annotations
import discord, io, os
from discord import app_commands
from discord.ext import commands
from pathlib import Path
from datetime import datetime, timezone, timedelta
from utils.db import ServerListDB, GuildDB
from utils.helpers import is_bot_admin

KST = timezone(timedelta(hours=9))


def _not_admin():
    class V(discord.ui.LayoutView):
        c = discord.ui.Container(discord.ui.TextDisplay("봇 관리자만 사용할 수 있습니다."), accent_color=0xED4245)
    return V(timeout=None)


class ServerAdminCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="서버삭제", description="DB에서 서버 삭제 + 백업파일 생성 (봇 관리자)")
    @app_commands.describe(서버id="삭제할 서버 ID")
    async def del_server(self, i: discord.Interaction, 서버id: str):
        if not is_bot_admin(i.user.id):
            await i.response.send_message(view=_not_admin(), ephemeral=True); return
        await i.response.defer(ephemeral=True)
        try: gid = int(서버id.strip())
        except ValueError:
            await i.followup.send(view=discord.ui.LayoutView(), ephemeral=True); return

        # 백업
        lines = []
        db_path = Path(f"SERVER/{gid}.db")
        if db_path.exists():
            try:
                gdb = GuildDB(gid)
                lines.append(f"=== 서버 {gid} 설정 ===")
                for k, v in gdb.all_cfg().items(): lines.append(f"{k}: {v}")
                lines.append("\n=== 카테고리/상품 ===")
                for cat in gdb.get_cats():
                    lines.append(f"  [{cat['id']}] {cat['name']}")
                    for p in gdb.get_prods(cat["id"]):
                        lines.append(f"    - {p['name']} | {p['price']}원 | 재고:{p['stock']}")
                gdb.c.close()
            except Exception as e: lines.append(f"백업 오류: {e}")

        sldb = ServerListDB()
        deleted = sldb.delete(gid)
        if db_path.exists(): os.remove(db_path)

        now_s = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
        file = discord.File(io.BytesIO(("\n".join(lines) or "데이터 없음").encode()),
                            filename=f"backup_{gid}_{now_s}.txt")
        gname = deleted["guild_name"] if deleted else "알 수 없음"

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 서버 삭제 완료\n서버명 : **{gname}**\nID : `{gid}`\n백업 파일 첨부됨"
                ),
                accent_color=0x57F287,
            )
        await i.followup.send(view=V(timeout=None), file=file, ephemeral=True)

    @app_commands.command(name="서버목록", description="입장 서버 목록 조회 (봇 관리자)")
    @app_commands.choices(상태=[
        app_commands.Choice(name="초대만 해둔 서버", value="invited"),
        app_commands.Choice(name="사용중인 서버", value="active"),
        app_commands.Choice(name="만료된 서버", value="expired"),
        app_commands.Choice(name="전체", value="all"),
    ])
    async def list_servers(self, i: discord.Interaction, 상태: str):
        if not is_bot_admin(i.user.id):
            await i.response.send_message(view=_not_admin(), ephemeral=True); return
        await i.response.defer(ephemeral=True)
        sm = {"invited":"초대됨","active":"사용중","expired":"만료"}
        recs = ServerListDB().get_all(None if 상태 == "all" else 상태)
        lines = [
            f"[{sm.get(r['status'],r['status'])}] {r['guild_name']} ({r['guild_id']}) | 만료:{(r.get('expires_at') or '-')[:10]}"
            for r in recs
        ]
        file = discord.File(io.BytesIO(("\n".join(lines) or "없음").encode()), filename=f"servers_{상태}.txt")
        lmap = {"invited":"초대됨","active":"사용중","expired":"만료","all":"전체"}

        class V(discord.ui.LayoutView):
            container = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 서버 목록 ({lmap.get(상태,상태)})\n총 **{len(recs)}개** 조회\n파일 첨부됨"
                ),
                accent_color=0x5865F2,
            )
        await i.followup.send(view=V(timeout=None), file=file, ephemeral=True)


async def setup(bot): await bot.add_cog(ServerAdminCog(bot))
