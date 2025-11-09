import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import datetime
import sqlite3
import os
from dotenv import load_dotenv
import requests

load_dotenv()

# --- 환경 변수 로드 ---
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
WEB_BASE_URL = os.getenv("WEB_BASE_URL", "http://localhost:5000") # 웹 서버 기본 주소
WEB_VERIFY_ENDPOINT = f"{WEB_BASE_URL}/verify" # /인증버튼을 통한 일반 인증 URL

# --- 명령어 사용 허용 유저 ID (여기서 변경!!! 실제 Discord 유저 ID로 변경하세요) ---
ALLOWED_USER_ID = 1402654236570812467 

# --- 봇 설정 ---
intents = discord.Intents.default()
intents.members = True
intents.invites = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- SQLite 유틸리티 함수 ---
def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# DB 테이블 초기화 (필요한 테이블이 없으면 생성)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joined_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TEXT,
            invite_code TEXT,
            invite_uses INTEGER,
            guild_id INTEGER
        )
    """)
    cursor.execute("""
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
    cursor.execute("""
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

# 길드 설정 조회
def get_guild_settings(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
    settings = cursor.fetchone()
    conn.close()
    return settings

# 길드 설정 업데이트/생성
def update_guild_setting(guild_id, key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    # ON CONFLICT 절은 SQLite 3.24.0 이상에서만 사용 가능합니다.
    # 이전 버전에서는 먼저 SELECT 후 INSERT/UPDATE를 수동으로 처리해야 합니다.
    cursor.execute(f"""
        INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET {key} = EXCLUDED.{key}
    """, (guild_id, value))
    conn.commit()
    conn.close()

# 복구 가능한 유저 수 조회
def get_recoverable_users_count(guild_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM verified_users WHERE guild_id = ?", (guild_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- 명령어 사용 권한 확인 (체크 데코레이터) ---
def is_allowed_user():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id == ALLOWED_USER_ID:
            return True
        else:
            await interaction.response.send_message("이 명령어는 지정된 사용자만 사용할 수 있습니다.", ephemeral=True)
            return False
    return app_commands.check(predicate)

# --- 봇 이벤트 핸들러 ---
@bot.event
async def on_ready():
    print(f'{bot.user.name} 봇이 온라인 상태입니다.')
    init_db() # 봇 시작 시 DB 초기화

    try:
        # 봇이 참여한 모든 길드의 설정을 불러와 View를 등록
        # 이렇게 등록해야 봇 재시작 후에도 이전 메시지의 버튼이 동작할 수 있습니다.
        if bot.guilds:
            for guild in bot.guilds:
                settings = get_guild_settings(guild.id)
                # 설정이 없을 경우 기본값 사용
                embed_title = settings["embed_title"] if settings else "서버 인증 안내"
                embed_description = settings["embed_description"] if settings else "서버의 모든 기능을 사용하려면 아래 버튼을 눌러 인증을 완료해주세요."
                # VerificationView는 버튼 style이 URL이므로 콜백 함수는 없습니다.
                # 그러나 add_view를 통해 메시지의 컴포넌트 상태를 유지합니다.
                bot.add_view(VerificationView(guild.id, embed_title, embed_description))
        else:
            print("봇이 참여하고 있는 길드가 없습니다. View를 등록할 수 없습니다.")
        
        await bot.tree.sync() # 슬래시 명령어 전역 동기화
        print("슬래시 명령어가 성공적으로 동기화되었습니다.")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")
    
# 새 멤버가 서버에 참여했을 때 (웹 인증 로깅과 겹치지 않게 처리)
@bot.event
async def on_member_join(member):
    guild = member.guild
    settings = get_guild_settings(guild.id)
    if settings and settings["log_channel_id"]:
        log_channel = guild.get_channel(settings["log_channel_id"])
        if log_channel:
            await log_channel.send(f"{member.name}({member.id})이(가) 서버에 입장했습니다.")

# --- `/복구` 명령어 (이전에 웹 인증한 모든 유저를 강제 참여) ---
@bot.tree.command(name="복구", description="이전에 웹 인증한 모든 유저를 현재 서버에 강제 참여시킵니다.")
@is_allowed_user() # 특정 유저만 사용 가능
async def recover_all_users_force_join(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.guild:
        await interaction.followup.send("이 명령어는 서버 내에서만 사용할 수 없습니다.", ephemeral=True)
        return
    
    try:
        # 웹 서버의 /force_join_all 엔드포인트를 호출하여 모든 유저를 서버에 추가 요청
        response = requests.post(f"{WEB_BASE_URL}/force_join_all", json={
            "guild_id": str(interaction.guild.id)
        })
        
        response_data = response.json()
        
        results_message = "### 유저 복구 결과:\n"
        # 복구 결과를 임베드로 만들 수도 있지만, 여기서는 간결한 텍스트로.
        for result in response_data.get("results", []):
            status_char = "성공" if result["success"] else "실패"
            results_message += f"- {status_char}: **{result['username']}** - {result['message']}\n"
        
        if not response_data.get("results"):
            results_message = "복구 요청을 처리할 수 있는 유저가 없거나 처리 중 오류가 발생했습니다."

        await interaction.followup.send(results_message, ephemeral=True)
        
        # 로그 기록
        settings = get_guild_settings(interaction.guild.id)
        if settings and settings["log_channel_id"]:
            log_channel = interaction.guild.get_channel(settings["log_channel_id"])
            if log_channel:
                log_message = f"관리자 {interaction.user.name}({interaction.user.id})이(가) 이전에 웹 인증한 모든 유저를 서버에 강제 참여시도했습니다:\n{results_message}"
                await log_channel.send(log_message)

    except requests.exceptions.RequestException as req_err:
        await interaction.followup.send(f"웹 서버와 통신 중 오류가 발생했습니다: {req_err}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"유저 강제 참여 중 알 수 없는 오류가 발생했습니다: {e}", ephemeral=True)

# --- `/로그채널` 명령어 (봇 활동 로그 채널 설정) ---
@bot.tree.command(name="로그채널", description="봇 활동 로그를 기록할 채널을 설정합니다.")
@is_allowed_user() # 특정 유저만 사용 가능
@app_commands.describe(channel="로그를 보낼 채널")
async def set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    update_guild_setting(interaction.guild_id, "log_channel_id", channel.id)
    await interaction.followup.send(f"로그 채널이 {channel.mention}으로 설정되었습니다.", ephemeral=True)
    await channel.send(f"봇 활동 로그 채널이 {interaction.user.name}에 의해 설정되었습니다.")

# --- `/역할` 명령어 (인증 완료 시 지급될 역할 설정) ---
@bot.tree.command(name="역할", description="인증 완료 시 지급될 역할을 설정합니다.")
@is_allowed_user() # 특정 유저만 사용 가능
@app_commands.describe(role="지급될 역할")
async def set_verified_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    if role >= interaction.guild.me.top_role:
        await interaction.followup.send("봇보다 높은 역할은 설정할 수 없습니다. 봇 역할 순서를 조정해주세요.", ephemeral=True)
        return
    update_guild_setting(interaction.guild_id, "verified_role_id", role.id)
    await interaction.followup.send(f"인증 완료 시 지급될 역할이 {role.mention}으로 설정되었습니다.", ephemeral=True)

# --- `/정보` 명령어 (서버 정보 표시) ---
@bot.tree.command(name="정보", description="현재 서버의 정보를 표시합니다.")
@is_allowed_user() # 특정 유저만 사용 가능
async def server_info(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    settings = get_guild_settings(guild.id)

    # 복구 가능한 인원수 조회
    recoverable_count = get_recoverable_users_count(guild.id)

    embed = discord.Embed(
        title=f"{guild.name} 서버 정보",
        description=f"서버 ID: {guild.id}",
        color=discord.Color.black() # 검정색 임베드
    )
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="서버 생성일", value=discord.utils.format_dt(guild.created_at, "R"), inline=True)
    embed.add_field(name="멤버 수", value=f"{guild.member_count}명", inline=True)
    embed.add_field(name="복구 가능한 인원", value=f"{recoverable_count}명", inline=True) # 복구 가능한 인원 추가
    
    owner = guild.owner if guild.owner else await bot.fetch_user(guild.owner_id)
    embed.add_field(name="서버 소유자", value=owner.name if owner else "정보 없음", inline=True)

    if settings:
        log_channel = guild.get_channel(settings["log_channel_id"]) if settings["log_channel_id"] else None
        verified_role = guild.get_role(settings["verified_role_id"]) if settings["verified_role_id"] else None
        
        embed.add_field(name="로그 채널", value=log_channel.mention if log_channel else "설정 안됨", inline=True)
        embed.add_field(name="인증 역할", value=verified_role.mention if verified_role else "설정 안됨", inline=True)
        embed.add_field(name="부계정 허용", value="허용" if settings["allow_alt_accounts"] else "불가능", inline=True)
        embed.add_field(name="VPN 허용", value="허용" if settings["allow_vpn"] else "불가능", inline=True)
        embed.add_field(name="임베드 제목", value=f"```\n{settings['embed_title']}\n```", inline=False)
        embed.add_field(name="임베드 설명", value=f"```\n{settings['embed_description']}\n```", inline=False)
    else:
        embed.add_field(name="봇 설정", value="아직 설정된 정보가 없습니다. 관리 명령어로 설정해주세요.", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)

# --- `/필터링설정` 명령어 (부계정, VPN 인증 가능 여부 설정) ---
@bot.tree.command(name="필터링설정", description="인증 시 부계정 및 VPN 허용 여부를 설정합니다.")
@is_allowed_user() # 특정 유저만 사용 가능
@app_commands.describe(
    alt_accounts="부계정 사용을 허용할까요?",
    vpn="VPN 사용을 허용할까요?"
)
async def set_filter_settings(interaction: discord.Interaction, alt_accounts: bool, vpn: bool):
    await interaction.response.defer(ephemeral=True)
    update_guild_setting(interaction.guild_id, "allow_alt_accounts", alt_accounts)
    update_guild_setting(interaction.guild_id, "allow_vpn", vpn)

    alt_status = "허용" if alt_accounts else "불가능"
    vpn_status = "허용" if vpn else "불가능"
    await interaction.followup.send(
        f"필터링 설정이 업데이트되었습니다:\n"
        f"- 부계정 사용: {alt_status}\n"
        f"- VPN 사용: {vpn_status}",
        ephemeral=True
    )

# --- `/내용` 명령어 (인증 임베드 내용 설정) ---
@bot.tree.command(name="내용", description="인증 임베드 메시지의 제목과 설명을 설정합니다.")
@is_allowed_user() # 특정 유저만 사용 가능
@app_commands.describe(
    title="임베드 제목 (최대 256자)",
    description="임베드 설명 (최대 4096자)"
)
async def set_embed_content(interaction: discord.Interaction, title: str, description: str):
    await interaction.response.defer(ephemeral=True)

    if len(title) > 256:
        await interaction.followup.send("임베드 제목은 256자를 초과할 수 없습니다.", ephemeral=True)
        return
    if len(description) > 4096:
        await interaction.followup.send("임베드 설명은 4096자를 초과할 수 없습니다.", ephemeral=True)
        return
    
    update_guild_setting(interaction.guild_id, "embed_title", title)
    update_guild_setting(interaction.guild_id, "embed_description", description)
    
    await interaction.followup.send("인증 임베드 제목과 설명이 설정되었습니다.", ephemeral=True)

# --- `VerificationView` 클래스 (인증 버튼을 포함하는 View) ---
class VerificationView(ui.View):
    def __init__(self, guild_id, embed_title, embed_description):
        super().__init__(timeout=None)
        # 버튼을 URL 타입으로 변경하여 클릭 시 바로 웹페이지로 이동
        verify_url = f"{WEB_VERIFY_ENDPOINT}?guild_id={guild_id}"
        self.add_item(ui.Button(label="인증하기", style=discord.ButtonStyle.link, url=verify_url))
        
        self.guild_id = guild_id # 로깅 등을 위해 guild_id 저장

    # style=discord.ButtonStyle.link 인 버튼은 콜백 함수가 실행되지 않습니다.

# --- `/인증버튼` 명령어 (인증 버튼이 포함된 임베드 메시지 전송) ---
@bot.tree.command(name="인증버튼", description="인증 버튼이 포함된 임베드 메시지를 현재 채널에 보냅니다.")
@is_allowed_user() # 특정 유저만 사용 가능
async def send_verification_button(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.guild:
        await interaction.followup.send("이 명령어는 서버 내에서만 사용할 수 없습니다.", ephemeral=True)
        return

    settings = get_guild_settings(interaction.guild.id)
    # 로그 채널과 역할이 설정되어 있는지 확인
    if not settings or not settings["log_channel_id"] or not settings["verified_role_id"]:
        await interaction.followup.send("서버 설정이 완료되지 않았습니다. /로그채널, /역할 명령어로 먼저 설정을 완료해주세요.", ephemeral=True)
        return
    
    embed_title = settings["embed_title"]
    embed_description = settings["embed_description"]

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Color.black() # 검정색 임베드
    )
    embed.add_field(name="진행 방법", value="아래 '인증하기' 버튼을 클릭하여 웹페이지에서 Discord 계정으로 인증을 완료해주세요.", inline=False)
    embed.set_footer(text="인증 시 관리자가 설정한 부계정 및 VPN 필터링이 적용될 수 있습니다.")

    view = VerificationView(interaction.guild.id, embed_title, embed_description)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("인증 버튼 메시지를 성공적으로 보냈습니다!", ephemeral=True)

# 봇 실행
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("DISCORD_BOT_TOKEN 환경 변수를 설정해주세요.")
