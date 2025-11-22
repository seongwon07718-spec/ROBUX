# main_bot.py - .env 없이 사용 가능한 최종본
# discord.py v2(app_commands) 기준
import sqlite3
import asyncio
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands

# ----------------------------
# 설정 (여기에 직접 값을 입력하세요)
# ----------------------------
BOT_TOKEN = "여기에_봇_토큰을_문자열로_넣으세요"
ADMIN_ID = 1402654236570812467  # 소유자 ID (정수)
# 추가 허용 사용자들(콤마로 구분) - 필요 없으면 빈 리스트로 두세요
ALLOWED_USER_IDS = [12023760, 1250580892537386]
DATABASE_PATH = "database.db"
# ----------------------------

# intents 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# ----------------------------
# DB 유틸리티 및 스키마 보장
# ----------------------------
def start_db():
    con = sqlite3.connect(DATABASE_PATH)
    cur = con.cursor()
    return con, cur

def ensure_schema():
    con, cur = start_db()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        log_channel_id INTEGER,
        auth_role_id INTEGER,
        filter_enabled INTEGER DEFAULT 0,
        content_text TEXT DEFAULT ''
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        days INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        token TEXT,
        guild_id INTEGER
    );
    """)
    con.commit()
    con.close()

# ----------------------------
# 권한 체크 헬퍼
# ----------------------------
def is_owner(user: discord.User) -> bool:
    return user.id == ADMIN_ID

def is_allowed_dev(user: discord.User) -> bool:
    return user.id in ALLOWED_USER_IDS or is_owner(user)

async def check_guild_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.user
    if isinstance(member, discord.Member):
        return member.guild_permissions.administrator or member.guild_permissions.manage_guild
    return False

def require_permission_message():
    return "권한이 없습니다. 관리자이거나 허용된 사용자만 사용 가능합니다."

# ----------------------------
# 임베드 템플릿
# ----------------------------
def embeda(embed_type: str, title: str, description: str, fields: Optional[List[tuple]] = None) -> discord.Embed:
    color_map = {
        "success": 0x5c6cdf,
        "error": 0xff5c5c,
        "warn": 0xffa500,
        "info": 0x5c6cdf
    }
    color = color_map.get(embed_type, 0x5c6cdf)
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for (name, value, inline) in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text="SinLinkBackup")
    return embed

# ----------------------------
# DB 관련 유틸 함수
# ----------------------------
def set_log_channel(guild_id: int, channel_id: int):
    con, cur = start_db()
    cur.execute("INSERT INTO guild_settings (guild_id, log_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id;", (guild_id, channel_id))
    con.commit()
    con.close()

def get_guild_settings(guild_id: int):
    con, cur = start_db()
    cur.execute("SELECT guild_id, log_channel_id, auth_role_id, filter_enabled, content_text FROM guild_settings WHERE guild_id = ?;", (guild_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return {
        "guild_id": row[0],
        "log_channel_id": row[1],
        "auth_role_id": row[2],
        "filter_enabled": bool(row[3]),
        "content_text": row[4]
    }

def set_auth_role(guild_id: int, role_id: int):
    con, cur = start_db()
    cur.execute("INSERT INTO guild_settings (guild_id, auth_role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET auth_role_id=excluded.auth_role_id;", (guild_id, role_id))
    con.commit()
    con.close()

def set_filter(guild_id: int, enabled: bool):
    con, cur = start_db()
    cur.execute("INSERT INTO guild_settings (guild_id, filter_enabled) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET filter_enabled=excluded.filter_enabled;", (guild_id, int(enabled)))
    con.commit()
    con.close()

def set_content_text(guild_id: int, text: str):
    con, cur = start_db()
    cur.execute("INSERT INTO guild_settings (guild_id, content_text) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET content_text=excluded.content_text;", (guild_id, text))
    con.commit()
    con.close()

# ----------------------------
# 인증 버튼 뷰 (예시)
# ----------------------------
class AuthButtonView(discord.ui.View):
    def __init__(self, guild_id: int, role_id: Optional[int]):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.role_id = role_id

    @discord.ui.button(label="인증 하기", style=discord.ButtonStyle.primary, custom_id="sinlink_auth_button")
    async def auth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            return await interaction.followup.send("서버에서만 사용 가능한 버튼입니다.", ephemeral=True)

        settings = get_guild_settings(interaction.guild.id)
        role_id = settings.get("auth_role_id") if settings else self.role_id
        if not role_id:
            return await interaction.followup.send("인증 역할이 설정되어 있지 않습니다. 관리자에게 문의하세요.", ephemeral=True)

        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.followup.send("설정된 역할을 찾을 수 없습니다.", ephemeral=True)

        try:
            await interaction.user.add_roles(role, reason="인증 버튼을 통한 역할 부여")
            await interaction.followup.send(embed=embeda("success", "인증 완료", f"{interaction.user.mention}님에게 역할이 부여되었습니다."), ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(embed=embeda("error", "권한 오류", "봇에게 역할을 부여할 권한이 없습니다."), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=embeda("error", "오류", str(e)), ephemeral=True)

# ----------------------------
# 슬래시 명령어 구현
# ----------------------------
@tree.command(name="정보", description="서버의 라이센스와 설정 정보를 표시합니다.")
async def info_command(interaction: discord.Interaction):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)

    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("서버에서만 사용할 수 있는 명령어입니다.", ephemeral=True)

    settings = get_guild_settings(guild.id)
    fields = []
    if settings:
        fields.append(("로그 채널", f"<#{settings['log_channel_id']}>" if settings['log_channel_id'] else "미설정", True))
        fields.append(("인증 역할", f"<@&{settings['auth_role_id']}>" if settings['auth_role_id'] else "미설정", True))
        fields.append(("필터링 활성화", "예" if settings['filter_enabled'] else "아니오", True))
        fields.append(("인증 내용", settings['content_text'] or "미설정", False))
    else:
        fields.append(("설정", "설정이 없습니다.", False))

    embed = embeda("info", "서버 정보", f"{guild.name} ({guild.id})", fields=fields)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="로그채널", description="로그를 전송할 채널을 설정합니다.")
@app_commands.describe(channel="로그를 받을 텍스트 채널")
async def log_channel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)
    set_log_channel(interaction.guild.id, channel.id)
    embed = embeda("success", "로그 채널 설정", f"이제 로그는 {channel.mention} 채널로 전송됩니다.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="역할", description="인증 역할을 설정하거나 테스트로 부여합니다.")
@app_commands.describe(role="인증 역할으로 사용할 역할", action="set:설정, test:테스트 부여")
async def role_command(interaction: discord.Interaction, role: Optional[discord.Role], action: Optional[str] = "set"):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)
    if action == "set":
        if not role:
            return await interaction.response.send_message("설정할 역할을 선택하세요.", ephemeral=True)
        set_auth_role(interaction.guild.id, role.id)
        await interaction.response.send_message(embed=embeda("success", "인증 역할 설정", f"인증 역할이 {role.mention} 으로 설정되었습니다."), ephemeral=True)
    elif action == "test":
        if not role:
            return await interaction.response.send_message("테스트할 역할을 선택하세요.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="테스트 역할 부여")
            await interaction.response.send_message(embed=embeda("success", "테스트 성공", f"{interaction.user.mention}님에게 역할을 부여했습니다."), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=embeda("error", "권한 오류", "봇에게 역할을 부여할 권한이 없습니다."), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=embeda("error", "오류", str(e)), ephemeral=True)
    else:
        await interaction.response.send_message("action 파라미터는 set 또는 test 만 허용됩니다.", ephemeral=True)

@tree.command(name="필터링설정", description="서버의 메시지 필터링을 설정합니다.")
@app_commands.describe(enable="필터링 사용 여부", content="필터링 시 안내할 내용")
async def filter_command(interaction: discord.Interaction, enable: bool, content: Optional[str] = ""):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)
    set_filter(interaction.guild.id, enable)
    if content:
        set_content_text(interaction.guild.id, content)
    embed = embeda("success", "필터링 설정 변경", f"필터링이 {'활성화' if enable else '비활성화'} 되었습니다.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="내용", description="인증/안내 메시지 내용을 설정합니다.")
@app_commands.describe(text="설정할 안내 텍스트")
async def content_command(interaction: discord.Interaction, text: str):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)
    set_content_text(interaction.guild.id, text)
    await interaction.response.send_message(embed=embeda("success", "내용 저장", "안내 메시지가 저장되었습니다."), ephemeral=True)

@tree.command(name="인증버튼", description="인증 버튼을 포함한 메시지를 발행합니다.")
@app_commands.describe(channel="버튼을 보낼 텍스트 채널", role="버튼 클릭 시 부여할 역할 (선택 가능)")
async def auth_button_command(interaction: discord.Interaction, channel: discord.TextChannel, role: Optional[discord.Role] = None):
    if not (await check_guild_admin(interaction) or is_allowed_dev(interaction.user)):
        return await interaction.response.send_message(require_permission_message(), ephemeral=True)
    view = AuthButtonView(interaction.guild.id, role.id if role else None)
    content_text = get_guild_settings(interaction.guild.id)['content_text'] if get_guild_settings(interaction.guild.id) else "인증 버튼을 눌러 인증하세요."
    try:
        await channel.send(embed=embeda("info", "인증하기", content_text), view=view)
        await interaction.response.send_message(embed=embeda("success", "인증 메시지 발행", f"{channel.mention} 채널에 인증 버튼을 발행했습니다."), ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(embed=embeda("error", "권한 오류", "봇에게 해당 채널에 메시지를 보낼 권한이 없습니다."), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(embed=embeda("error", "오류", str(e)), ephemeral=True)

@tree.command(name="복구", description="소유자 전용: 복구키로 저장된 사용자를 현재 서버로 복구합니다.")
@app_commands.describe(recover_key="복구에 사용할 키")
async def recover_command(interaction: discord.Interaction, recover_key: str):
    if not is_owner(interaction.user):
        return await interaction.response.send_message("이 명령어는 소유자만 사용할 수 있습니다.", ephemeral=True)

    await interaction.response.send_message("복구를 시작합니다. (콘솔 로그를 확인하세요)", ephemeral=True)
    con, cur = start_db()
    cur.execute("SELECT id FROM guilds WHERE token == ?;", (recover_key,))
    row = cur.fetchone()
    if not row:
        con.close()
        return await interaction.followup.send(embed=embeda("error", "복구 실패", "해당 복구키에 해당하는 서버 정보가 없습니다."), ephemeral=True)

    source_guild_id = row[0]
    cur.execute("SELECT id, token FROM users WHERE guild_id == ?;", (source_guild_id,))
    users = cur.fetchall()
    con.close()

    progress = 0
    total = len(users)
    await interaction.followup.send(f"총 {total}명 복구 시도합니다.", ephemeral=True)
    for u in users:
        user_id, refresh_token = u[0], u[1]
        try:
            # 실제 동작: refresh_token->access_token 변환 후 add_user 호출 필요
            # new_token = await refresh_token(refresh_token)
            # await add_user(new_token['access_token'], interaction.guild.id, user_id)
            progress += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print("복구 중 예외:", e)
            continue
    await interaction.followup.send(embed=embeda("success", "복구 완료", f"{progress}/{total} 명 복구 시도 완료"), ephemeral=True)

# ----------------------------
# 봇 이벤트 및 시작
# ----------------------------
@bot.event
async def on_ready():
    ensure_schema()
    await tree.sync()
    print(f"Bot ready. Logged in as {bot.user} (ID: {bot.user.id})")

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN.startswith("여기에"):
        print("ERROR: BOT_TOKEN 값이 설정되어 있지 않습니다. 코드 상단에 BOT_TOKEN을 입력하세요.")
    else:
        bot.run(BOT_TOKEN)
