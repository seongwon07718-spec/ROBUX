import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
import datetime
import requests

# --- 직접 입력하는 환경 변수 ---
BOT_TOKEN = "여기에_봇_토큰_입력"
WEB_BASE_URL = "http://localhost:5000"
WEB_VERIFY_ENDPOINT = f"{WEB_BASE_URL}/verify"
ALLOWED_USER_ID = 1402654236570812467  # 실제 Discord ID로 변경 필수

# --- 봇 초기 설정 ---
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- DB 유틸리티 ---
def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            log_channel_id INTEGER,
            verified_role_id INTEGER,
            allow_alt_accounts BOOLEAN DEFAULT 0,
            allow_vpn BOOLEAN DEFAULT 0,
            embed_title TEXT DEFAULT '서버 인증 안내',
            embed_description TEXT DEFAULT '서버의 모든 기능을 사용하려면 아래 버튼을 눌러 인증을 완료해주세요.'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            username TEXT,
            verified_at TEXT,
            is_alt_account BOOLEAN DEFAULT 0,
            is_vpn_user BOOLEAN DEFAULT 0,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TEXT,
            FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
        )
    """)
    conn.commit()
    conn.close()

def get_guild_settings(guild_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
    result = cur.fetchone()
    conn.close()
    return result

def update_guild_setting(guild_id, key, value):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET {key} = excluded.{key}
    """, (guild_id, value))
    conn.commit()
    conn.close()

def get_recoverable_users_count(guild_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM verified_users WHERE guild_id = ?", (guild_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

# --- 명령어 사용 권한 제한 ---
def is_allowed_user():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == ALLOWED_USER_ID:
            return True
        await interaction.response.send_message('이 명령어는 권한이 있는 사용자만 사용할 수 있습니다.', ephemeral=True)
        return False
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    init_db()
    # 모든 길드에 대해 VerificationView 등록
    for guild in bot.guilds:
        settings = get_guild_settings(guild.id)
        embed_title = settings['embed_title'] if settings else '서버 인증 안내'
        embed_desc = settings['embed_description'] if settings else '서버의 모든 기능을 사용하려면 아래 버튼을 눌러 인증을 완료해주세요.'
        bot.add_view(VerificationView(guild.id, embed_title, embed_desc))
    await bot.tree.sync()
    print(f'{bot.user} 봇 실행 완료!')

# --- /복구 명령어 ---
@bot.tree.command(name="복구", description="서버에 인증된 모든 유저를 강제 복구합니다.")
@is_allowed_user()
async def cmd_recover(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id

    try:
        res = requests.post(f"{WEB_BASE_URL}/force_join_all", json={"guild_id": str(guild_id)})
        data = res.json()
        result_msg = "복구 결과:\n"
        for r in data.get('results', []):
            status = "성공" if r['success'] else "실패"
            result_msg += f"- {r['username']}: {status} - {r['message']}\n"
        if not data.get('results'):
            result_msg = "복구 가능한 유저가 없습니다."
        await interaction.followup.send(result_msg, ephemeral=True)

        settings = get_guild_settings(guild_id)
        if settings and settings['log_channel_id']:
            channel = interaction.guild.get_channel(settings['log_channel_id'])
            if channel:
                await channel.send(f"{interaction.user}님이 인증된 모든 유저 복구를 시도했습니다.\n{result_msg}")

    except Exception as e:
        await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)

# --- /로그채널 명령어 ---
@bot.tree.command(name="로그채널", description="로그 채널을 설정합니다.")
@is_allowed_user()
@app_commands.describe(channel="로그를 받을 채널을 선택하세요.")
async def cmd_set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    update_guild_setting(interaction.guild.id, 'log_channel_id', channel.id)
    await interaction.response.send_message(f"로그 채널을 {channel.mention} 으로 설정했습니다.", ephemeral=True)
    await channel.send(f"로그 채널이 {interaction.user}님에 의해 설정되었습니다.")

# --- /역할 명령어 ---
@bot.tree.command(name="역할", description="인증 완료 시 지급할 역할을 설정합니다.")
@is_allowed_user()
@app_commands.describe(role="역할 선택")
async def cmd_set_verified_role(interaction: discord.Interaction, role: discord.Role):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("봇 역할보다 높은 역할은 설정할 수 없습니다.", ephemeral=True)
        return
    update_guild_setting(interaction.guild.id, 'verified_role_id', role.id)
    await interaction.response.send_message(f"인증 완료 역할을 {role.mention} 으로 설정했습니다.", ephemeral=True)

# --- /정보 명령어 ---
@bot.tree.command(name="정보", description="서버 정보를 표시합니다.")
@is_allowed_user()
async def cmd_server_info(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)
    recover_count = get_recoverable_users_count(interaction.guild.id)

    embed = discord.Embed(title=f"{interaction.guild.name} 서버 정보",
                          description=f"서버 ID: {interaction.guild.id}",
                          color=discord.Color.black())
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.add_field(name="서버 생성일", value=discord.utils.format_dt(interaction.guild.created_at, "R"), inline=True)
    embed.add_field(name="멤버 수", value=str(interaction.guild.member_count), inline=True)
    embed.add_field(name="복구 가능한 인원", value=str(recover_count), inline=True)

    owner = interaction.guild.owner or await bot.fetch_user(interaction.guild.owner_id)
    embed.add_field(name="서버 소유자", value=owner.name if owner else "정보 없음", inline=True)
    if settings:
        lc = interaction.guild.get_channel(settings['log_channel_id']) if settings['log_channel_id'] else "없음"
        vr = interaction.guild.get_role(settings['verified_role_id']) if settings['verified_role_id'] else "없음"
        embed.add_field(name="로그 채널", value=lc.mention if isinstance(lc, discord.TextChannel) else lc, inline=True)
        embed.add_field(name="인증 역할", value=vr.mention if isinstance(vr, discord.Role) else vr, inline=True)
        embed.add_field(name="부계정 허용", value="허용" if settings['allow_alt_accounts'] else "불가", inline=True)
        embed.add_field(name="VPN 허용", value="허용" if settings['allow_vpn'] else "불가", inline=True)
        embed.add_field(name="임베드 제목", value=settings['embed_title'], inline=False)
        embed.add_field(name="임베드 설명", value=settings['embed_description'], inline=False)
    else:
        embed.add_field(name="봇 설정", value="설정이 필요합니다.", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- /필터링설정 명령어 ---
@bot.tree.command(name="필터링설정", description="부계정 및 VPN 허용 여부 설정")
@is_allowed_user()
@app_commands.describe(alt_accounts="부계정 허용", vpn="VPN 허용")
async def cmd_set_filter_settings(interaction: discord.Interaction, alt_accounts: bool, vpn: bool):
    update_guild_setting(interaction.guild.id, 'allow_alt_accounts', alt_accounts)
    update_guild_setting(interaction.guild.id, 'allow_vpn', vpn)
    await interaction.response.send_message(f"설정이 저장되었습니다.\n부계정: {'허용' if alt_accounts else '불가'}\nVPN: {'허용' if vpn else '불가'}", ephemeral=True)

# --- /내용 명령어 ---
@bot.tree.command(name="내용", description="임베드 제목 및 설명 설정")
@is_allowed_user()
@app_commands.describe(title="임베드 제목", description="임베드 설명")
async def cmd_set_embed_content(interaction: discord.Interaction, title: str, description: str):
    if len(title) > 256:
        await interaction.response.send_message("임베드 제목은 256자 이내로 입력해주세요.", ephemeral=True)
        return
    if len(description) > 4096:
        await interaction.response.send_message("임베드 설명은 4096자 이내로 입력해주세요.", ephemeral=True)
        return
    update_guild_setting(interaction.guild.id, 'embed_title', title)
    update_guild_setting(interaction.guild.id, 'embed_description', description)
    await interaction.response.send_message("임베드 내용이 저장되었습니다.", ephemeral=True)

class VerificationView(ui.View):
    def __init__(self, guild_id, embed_title, embed_description):
        super().__init__(timeout=None)
        verify_url = f"{WEB_VERIFY_ENDPOINT}?guild_id={guild_id}"
        self.add_item(ui.Button(label="인증하기", style=discord.ButtonStyle.link, url=verify_url))

@bot.tree.command(name="인증버튼", description="인증 버튼 임베드 전송")
@is_allowed_user()
async def cmd_send_verification_button(interaction: discord.Interaction):
    settings = get_guild_settings(interaction.guild.id)
    if not settings or not settings['log_channel_id'] or not settings['verified_role_id']:
        await interaction.response.send_message("먼저 /로그채널, /역할 명령어로 설정해주세요.", ephemeral=True)
        return
    embed = discord.Embed(
        title=settings['embed_title'],
        description=settings['embed_description'],
        color=discord.Color.black()
    )
    embed.add_field(name="진행 방법", value="아래 인증하기 버튼을 눌러 웹 인증을 완료하세요.", inline=False)
    embed.set_footer(text="부계정 및 VPN 필터링이 적용될 수 있습니다.")
    view = VerificationView(interaction.guild.id, settings['embed_title'], settings['embed_description'])
    await interaction.response.send_message(embed=embed, view=view)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
