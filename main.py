import discord
from discord import app_commands
import sqlite3
import io
import time

@bot.tree.command(name="유저정보", description="특정 유저의 상세 정보와 거래 내역을 확인합니다.")
@app_commands.describe(유저="정보를 조회할 유저", 파일="텍스트 파일로 내보내기 여부")
@app_commands.choices(파일=[
    app_commands.Choice(name="파일로 받기", value="yes"),
    app_commands.Choice(name="파일 받지 않기", value="no")
])
async def user_info_manage(interaction: discord.Interaction, 유저: discord.Member, 파일: str = "no"):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("관리자 권한이 필요합니다.", ephemeral=True)

    u_id = str(유저.id)
    conn = sqlite3.connect('vending_data.db')
    cur = conn.cursor()

    # 유저 기본 정보 조회
    cur.execute("SELECT money, total_spent, is_blacked FROM users WHERE user_id = ?", (u_id,))
    user_row = cur.fetchone()
    
    # 거래 내역 조회 (최근 10개)
    cur.execute("SELECT amount, date, method FROM charge_logs WHERE user_id = ? ORDER BY date DESC LIMIT 10", (u_id,))
    logs = cur.fetchall()
    conn.close()

    if not user_row:
        return await interaction.response.send_message("해당 유저의 데이터가 존재하지 않습니다.", ephemeral=True)

    money, total_spent, is_blacked = user_row
    black_status = "O" if is_blacked == 1 else "X"

    # 1. 파일 옵션을 선택한 경우
    if 파일 == "yes":
        report_text = f"=== 유저 정보 보고서 ===\n"
        report_text += f"대상 유저: {유저.display_name} ({유저.id})\n"
        report_text += f"보유 잔액: {money:,}원\n"
        report_text += f"누적 충전: {total_spent:,}원\n"
        report_text += f"블랙 여부: {black_status}\n\n"
        report_text += "--- 최근 거래 내역 (최대 10개) ---\n"
        
        if logs:
            for l in logs:
                report_text += f"[{l[1]}] {l[2]}: {l[0]:,}원\n"
        else:
            report_text += "거래 내역이 없습니다.\n"

        file = discord.File(io.BytesIO(report_text.encode('utf-8')), filename=f"user_info_{u_id}.txt")
        return await interaction.response.send_message(f"**{유저.display_name}**님의 상세 정보 파일입니다.", file=file, ephemeral=True)

    # 2. 파일 옵션을 선택하지 않은 경우 (셀렉트 메뉴 방식)
    container = ui.Container(ui.TextDisplay(f"## 👤 {유저.display_name}님의 정보"), accent_color=0xffffff)
    container.add_item(ui.TextDisplay(f"보유 잔액: **{money:,}원**\n누적 충전: **{total_spent:,}원**\n블랙 여부: **{black_status}**"))
    
    # 거래 내역 확인을 위한 셀렉트 메뉴
    select_options = [
        discord.SelectOption(label="최근 거래 내역 확인", value="view_logs", emoji="📜")
    ]
    
    select_menu = ui.Select(placeholder="확인할 항목을 선택하세요", options=select_options)

    async def select_callback(it: discord.Interaction):
        if select_menu.values[0] == "view_logs":
            log_con = ui.Container(ui.TextDisplay(f"## {유저.display_name}님의 최근 내역"), accent_color=0x5865F2)
            if logs:
                log_text = "\n".join([f"• {l[1]} | {l[2]} | {l[0]:,}원" for l in logs])
                log_con.add_item(ui.TextDisplay(log_text))
            else:
                log_con.add_item(ui.TextDisplay("거래 내역이 존재하지 않습니다."))
            
            await it.response.send_message(view=ui.LayoutView().add_item(log_con), ephemeral=True)

    select_menu.callback = select_callback
    container.add_item(ui.ActionRow(select_menu))
    
    await interaction.response.send_message(view=ui.LayoutView().add_item(container), ephemeral=True)
