from __future__ import annotations
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from utils.db import GuildDB
from utils.helpers import is_guild_admin, is_registered, fmt, log


def _check(i: discord.Interaction):
    if not is_registered(i.guild.id): 
        return "not_reg"
    if not is_guild_admin(i.user):    
        return "not_admin"
    return None


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


# ─── 내역 조회 Select ─────────────────────────────────────
class HistSelect(discord.ui.Select):
    def __init__(self, gid, target_id):
        self.gid = gid
        self.target_id = target_id
        super().__init__(
            placeholder="내역 조회",
            options=[
                discord.SelectOption(label="최근 충전 내역", value="charge"),
                discord.SelectOption(label="최근 구매 내역", value="purchase"),
            ]
        )

    async def callback(self, i: discord.Interaction):
        gdb = GuildDB(self.gid)
        if self.values[0] == "charge":
            recs = gdb.recent_charges(self.target_id)
            sm = {"pending":"대기", "confirmed":"완료", "cancelled":"취소"}
            txt = "## 최근 충전 내역\n" + (
                "\n".join(f"• {fmt(r['amount'])} | {sm.get(r['status'], r['status'])} | {r['date'][:10]}" for r in recs)
                if recs else "없음"
            )
        else:
            recs = gdb.recent_purchases(self.target_id)
            txt = "## 최근 구매 내역\n" + (
                "\n".join(f"• {r['name']} x{r['qty']} | {fmt(r['price'])} | {r['date'][:10]}" for r in recs)
                if recs else "없음"
            )

        # TextDisplay 내용 업데이트
        self.view.container[0].content = txt
        await i.response.edit_message(view=self.view)


# ─── 유저 정보 뷰 ─────────────────────────────────────────
class UserInfoView(discord.ui.LayoutView):
    def __init__(self, gid, target: discord.Member, user_data):
        super().__init__(timeout=120)
        self.gid = gid

        self.container = discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 유저 정보\n"
                f"유저 : {target.mention}\n"
                f"잔액 : **{fmt(user_data['balance'])}**\n"
                f"누적 구매 : **{fmt(user_data['total_spent'])}**\n"
                f"할인율 : **{user_data['discount_rate']}%**"
            ),
            discord.ui.Separator(),
            accent_color=0x5865F2,
        )
        self.add_item(discord.ui.ActionRow(HistSelect(gid, target.id)))


class UserAdminCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot

    @app_commands.command(name="유저정보", description="자판기 유저 정보 조회 (서버 관리자)")
    @app_commands.describe(유저="조회할 유저")
    async def user_info(self, i: discord.Interaction, 유저: discord.Member):
        err = _check(i)
        if err == "not_reg":
            await i.response.send_message(view=_no_reg(), ephemeral=True)
            return
        if err == "not_admin":
            await i.response.send_message(view=_no_admin(), ephemeral=True)
            return

        gdb = GuildDB(i.guild.id)
        ud = gdb.get_user(유저.id)
        await i.response.send_message(
            view=UserInfoView(i.guild.id, 유저, ud), 
            ephemeral=True
        )

    @app_commands.command(name="잔액관리", description="유저 잔액 추가 / 차감 (서버 관리자)")
    @app_commands.describe(유저="대상 유저", 금액="금액", 여부="추가 또는 차감")
    @app_commands.choices(여부=[
        app_commands.Choice(name="추가", value="add"),
        app_commands.Choice(name="차감", value="sub"),
    ])
    async def balance_manage(self, i: discord.Interaction, 유저: discord.Member, 금액: int, 여부: str):
        err = _check(i)
        if err == "not_reg":
            await i.response.send_message(view=_no_reg(), ephemeral=True)
            return
        if err == "not_admin":
            await i.response.send_message(view=_no_admin(), ephemeral=True)
            return

        if 금액 <= 0:
            class Ve(discord.ui.LayoutView):
                c = discord.ui.Container(
                    discord.ui.TextDisplay("금액은 0보다 커야 합니다."), 
                    accent_color=0xED4245
                )
            await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
            return

        gdb = GuildDB(i.guild.id)
        before = gdb.get_user(유저.id)["balance"]

        if 여부 == "add":
            gdb.add_balance(유저.id, 금액)
            action = "추가"
        else:
            if before < 금액:
                class Ve(discord.ui.LayoutView):
                    c = discord.ui.Container(
                        discord.ui.TextDisplay(f"잔액 부족: 보유 {fmt(before)} < 차감 {fmt(금액)}"),
                        accent_color=0xED4245,
                    )
                await i.response.send_message(view=Ve(timeout=None), ephemeral=True)
                return
            gdb.add_balance(유저.id, -금액)
            action = "차감"

        after = gdb.get_user(유저.id)["balance"]

        class V(discord.ui.LayoutView):
            c = discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 잔액 {action} 완료\n"
                    f"유저 : {유저.mention}\n"
                    f"{action} : **{fmt(금액)}**\n"
                    f"이전 : {fmt(before)} → 현재 : **{fmt(after)}**"
                ),
                accent_color=0x57F287,
            )
        await i.response.send_message(view=V(timeout=None), ephemeral=True)

        asyncio.create_task(log(i.guild.id, "admin_log",
            f"잔액 관리 | 관리자: {i.user} | 유저: {유저} | {action}: {fmt(금액)} | {fmt(before)} → {fmt(after)}"))


async def setup(bot): 
    await bot.add_cog(UserAdminCog(bot))
