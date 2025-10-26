# bot_main.py (최종본)
import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

# 관리자 역할 ID 설정(여기에 실제 관리자 역할 ID를 넣으세요)
# 또는 환경변수 ADMIN_ROLE_ID로 설정해 사용할 수도 있습니다.
ADMIN_ROLE_ID = int(os.environ.get("ADMIN_ROLE_ID", "123456789012345678"))

# boost_module.py가 같은 폴더에 있어야 합니다.
import boost_module

intents = discord.Intents.default()
# interaction.user.roles를 사용하려면 guild intents가 필요할 수 있습니다.
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def is_admin_member(user: discord.abc.User) -> bool:
    """
    interaction.user는 Member일 수도 있고 User일 수도 있으므로 안전하게 체크합니다.
    가능한 경우 역할 기반으로 ADMIN_ROLE_ID를 확인합니다.
    """
    try:
        # Member인 경우 roles 속성 존재 -> 역할 검사
        if isinstance(user, discord.Member):
            return any(r.id == ADMIN_ROLE_ID for r in user.roles)
        # Interaction의 user가 Member가 아닐 경우(예: DM) False 처리
        return False
    except Exception:
        return False

@bot.tree.command(name="부스트_진행", description="서버 초대코드로 부스트를 진행합니다. (관리자 전용)")
@app_commands.describe(invite="초대 코드 또는 초대 링크", months="기간: 1 또는 3 (월)", amount="총 부스트 수(짝수)", nickname="서버 닉네임(선택)", validate="시작 전에 토큰 검증 여부")
async def slash_boost(interaction: discord.Interaction, invite: str, months: int, amount: int, nickname: str = "", validate: bool = False):
    # 권한 확인
    # interaction.user는 Member 타입일 가능성이 높으므로 변환 시 안전하게 처리
    member = None
    if isinstance(interaction.user, discord.Member):
        member = interaction.user
    else:
        # guild에서 멤버 객체로 다시 가져오기 시도 (명령이 guild에서 호출된 경우)
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = interaction.user

    if not is_admin_member(member):
        await interaction.response.send_message("권한이 없습니다. 관리자 역할이 필요합니다.", ephemeral=True)
        return

    # 파라미터 검증
    if months not in (1, 3):
        await interaction.response.send_message("months는 1 또는 3만 가능합니다.", ephemeral=True)
        return
    try:
        amount = int(amount)
    except:
        await interaction.response.send_message("amount는 숫자여야 합니다.", ephemeral=True)
        return
    if amount % 2 != 0:
        await interaction.response.send_message("amount는 짝수여야 합니다.", ephemeral=True)
        return

    await interaction.response.send_message("부스트 작업을 시작합니다. 완료 시 DM으로 결과를 전송합니다.", ephemeral=True)

    async def _run_boost():
        # 토큰 검증 옵션
        if validate:
            filename = "input/1m_tokens.txt" if months == 1 else "input/3m_tokens.txt"
            # validate_tokens_file은 블로킹이므로 to_thread로 실행
            valid, total = await asyncio.to_thread(boost_module.validate_tokens_file, filename)
            if valid == 0:
                return {"status": "failed", "reason": "유효한 토큰이 없습니다.", "valid": valid, "total": total}
            if valid * 2 < amount:
                return {"status": "failed", "reason": "유효한 토큰 부족", "valid": valid, "total": total}

        # 실제 부스트 실행 (블로킹 함수) -> to_thread 사용
        res = await asyncio.to_thread(boost_module.thread_boost, invite, amount, months, nickname)
        return {"status": "done", "result": res, "successful": len(boost_module.variables.success_tokens)*2, "failed": len(boost_module.variables.failed_tokens)*2}

    res = await _run_boost()

    # 결과 전송
    if res.get("status") == "done":
        msg = f"부스트 작업이 완료되었습니다.\n성공: {res.get('successful')} / 실패: {res.get('failed')}"
    else:
        msg = f"부스트 작업 실패: {res.get('reason')} (유효: {res.get('valid')}/{res.get('total')})"

    try:
        await interaction.user.send(msg)
    except Exception:
        # DM 차단 등으로 실패하면 명령 채널에 알림(관리자 전용 채널에서 사용하는 것을 권장)
        try:
            await interaction.channel.send(msg)
        except Exception:
            pass

@bot.tree.command(name="재고_추가하기", description="토큰을 재고에 추가합니다. (관리자 전용)")
@app_commands.describe(months="기간: 1 또는 3 (월)", tokens_text="토큰 목록(멀티라인, 선택)", tokens_file="토큰 파일 첨부(선택)")
async def slash_add_stock(interaction: discord.Interaction, months: int, tokens_text: str = None, tokens_file: discord.Attachment = None):
    # 권한 확인
    member = None
    if isinstance(interaction.user, discord.Member):
        member = interaction.user
    else:
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = interaction.user

    if not is_admin_member(member):
        await interaction.response.send_message("권한이 없습니다. 관리자 역할이 필요합니다.", ephemeral=True)
        return

    if months not in (1, 3):
        await interaction.response.send_message("months는 1 또는 3만 가능합니다.", ephemeral=True)
        return

    if not tokens_text and not tokens_file:
        await interaction.response.send_message("토큰을 텍스트로 붙여넣거나 파일을 첨부해 주세요.", ephemeral=True)
        return

    await interaction.response.send_message("토큰을 접수했습니다. 검사 및 추가를 진행합니다. 완료 시 DM으로 결과를 알려드립니다.", ephemeral=True)

    # 토큰 수집
    tokens = []
    if tokens_text:
        for line in tokens_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                parts = line.split(":")
                token = parts[-1].strip()
            else:
                token = line
            tokens.append(token)

    if tokens_file:
        # 첨부 파일은 메모리로 바로 읽어서 처리 (임시파일 없이)
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(tokens_file.url) as resp:
                    # 텍스트로 바로 읽음 (대부분 토큰 파일은 텍스트)
                    content = await resp.text()
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    parts = line.split(":")
                    token = parts[-1].strip()
                else:
                    token = line
                tokens.append(token)
        except Exception:
            # 다운로드 실패 시 빈 토큰 목록으로 넘어감 (이미 입력된 tokens_text는 유지)
            pass

    async def _check_and_add(tokens_list):
        filename = "input/1m_tokens.txt" if months == 1 else "input/3m_tokens.txt"
        valid_tokens = []
        invalid_count = 0
        for idx, tok in enumerate(tokens_list, start=1):
            # check_discord_token은 블로킹이므로 to_thread로 호출
            ok = await asyncio.to_thread(boost_module.check_discord_token, tok, True, idx)
            if ok:
                valid_tokens.append(tok)
            else:
                invalid_count += 1
                try:
                    open("invalid_tokens.txt", "a", encoding="utf-8").write(f"{tok}\n")
                except Exception:
                    pass
        if valid_tokens:
            try:
                with open(filename, "a", encoding="utf-8") as f:
                    for t in valid_tokens:
                        f.write(f"{t}\n")
            except Exception:
                pass
        # SQLite 로깅 (boost_module에 log_stock 함수 있음)
        try:
            boost_module.log_stock("add", months, len(valid_tokens), invalid_count, detail="source:discord_command")
        except Exception:
            pass
        return {"added": len(valid_tokens), "invalid": invalid_count, "total": len(tokens_list)}

    summary = await _check_and_add(tokens)

    # 결과 전송
    try:
        await interaction.user.send(f"재고 추가 완료: 총 {summary['total']}개 중 추가된 유효 토큰 {summary['added']}개, 무효 {summary['invalid']}개")
    except Exception:
        try:
            await interaction.channel.send(f"재고 추가 완료: 총 {summary['total']}개 중 추가된 유효 토큰 {summary['added']}개, 무효 {summary['invalid']}개")
        except Exception:
            pass

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        await bot.tree.sync()
    except Exception as e:
        print("tree sync error:", e)

if __name__ == "__main__":
    DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    if not DISCORD_BOT_TOKEN:
        print("환경변수 DISCORD_BOT_TOKEN 설정 필요")
        exit(1)
    bot.run(DISCORD_BOT_TOKEN)
