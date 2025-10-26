# bot_main.py (Pycord / 컴포넌트 v2 Container + TextDisplay 사용 최종본)
import os
import asyncio
import aiohttp
from datetime import datetime

# Pycord(또는 컴포넌트 v2 지원 라이브러리)에서 제공하는 ui 모듈 사용
# py-cord의 경우: from discord import ui, Colour, Interaction, Client 등
import discord
from discord import ui, Colour
from discord.ext import commands

# 관리자 역할 ID를 실제 값으로 바꿔주세요
ADMIN_ROLE_ID = int(os.environ.get("ADMIN_ROLE_ID", "123456789012345678"))

# 기존 부스트 로직 모듈
import boost_module

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 재고 갱신 태스크 보관: message.id -> asyncio.Task
_inventory_refresh_tasks = {}

def is_admin_member(member: discord.Member) -> bool:
    try:
        if isinstance(member, discord.Member):
            return any(r.id == ADMIN_ROLE_ID for r in member.roles)
        return False
    except Exception:
        return False

# ------------------ Component v2 스타일: Container / TextDisplay 레이아웃 ------------------
# 이 코드는 py-cord(컴포넌트 v2)를 기준으로 작성되었습니다.
class StockLayout(ui.Layout):
    """
    Container + TextDisplay 기반 레이아웃 (컴포넌트 v2)
    - 구성: Container(텍스트 블록)로 제목/막대/수치/안내를 보여줍니다.
    """
    def __init__(self, valid_count: int, invalid_count: int):
        super().__init__()
        self.valid = int(valid_count)
        self.invalid = int(invalid_count)
        self._build()

    def _make_bar(self, value, total, length=24):
        if total <= 0:
            total = 1
        filled = int((value / total) * length)
        filled = max(0, min(length, filled))
        return "█" * filled + "─" * (length - filled)

    def _build(self):
        total = self.valid + self.invalid if (self.valid + self.invalid) > 0 else 1
        # Container(Primary) - 제목
        c_title = ui.Container(ui.TextDisplay("EMOJI_0 재고 추가 결과"))
        c_title.accent_color = Colour.blurple()
        self.add_item(c_title)

        # Container - progress bar (valid)
        bar_v = self._make_bar(self.valid, total)
        c_bar_v = ui.Container(ui.TextDisplay(f"`{bar_v}`"))
        c_bar_v.accent_color = Colour.green()
        self.add_item(c_bar_v)

        # Container - valid count
        c_valid = ui.Container(ui.TextDisplay(f"**유효 토큰** = __{self.valid}개__"))
        self.add_item(c_valid)

        # Container - progress bar (invalid)
        bar_i = self._make_bar(self.invalid, total)
        c_bar_i = ui.Container(ui.TextDisplay(f"`{bar_i}`"))
        c_bar_i.accent_color = Colour.red()
        self.add_item(c_bar_i)

        # Container - invalid count
        c_invalid = ui.Container(ui.TextDisplay(f"**무효 토큰** = __{self.invalid}개__"))
        self.add_item(c_invalid)

        # Container - 안내문
        c_info = ui.Container(ui.TextDisplay("무효 토큰은 **File**(invalid_tokens.txt)로 확인 가능합니다"))
        self.add_item(c_info)

    def update(self, valid_count: int, invalid_count: int):
        # 레이아웃을 재생성해서 교체(간단한 방법)
        self.valid = int(valid_count)
        self.invalid = int(invalid_count)
        # clear existing and rebuild
        self.clear_items()
        self._build()

# helper: 게시 시간 표시 용(선택)
def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# ------------------ 슬래시 명령: /부스트_진행 ------------------
@bot.tree.command(name="부스트_진행", description="서버 초대코드로 부스트를 진행합니다. (관리자 전용)")
@discord.app_commands.describe(invite="초대 코드 또는 초대 링크", months="기간: 1 또는 3 (월)", amount="총 부스트 수(짝수)", nickname="서버 닉네임(선택)", validate="시작 전에 토큰 검증 여부 (True/False)")
async def slash_boost(interaction: discord.Interaction, invite: str, months: int, amount: int, nickname: str = "", validate: bool = False):
    # 멤버 확보 및 권한 확인
    member = interaction.user
    if not isinstance(member, discord.Member) and interaction.guild:
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
    try:
        amount = int(amount)
    except:
        await interaction.response.send_message("amount는 숫자여야 합니다.", ephemeral=True)
        return
    if amount % 2 != 0:
        await interaction.response.send_message("amount는 짝수여야 합니다.", ephemeral=True)
        return

    await interaction.response.send_message("부스트 작업을 시작합니다. 완료 시 결과를 알려드리겠습니다.", ephemeral=True)

    async def _run():
        if validate:
            filename = "input/1m_tokens.txt" if months == 1 else "input/3m_tokens.txt"
            valid, total = await asyncio.to_thread(boost_module.validate_tokens_file, filename)
            if valid == 0:
                return {"status": "failed", "reason": "유효한 토큰이 없습니다.", "valid": valid, "total": total}
            if valid * 2 < amount:
                return {"status": "failed", "reason": "유효한 토큰 부족", "valid": valid, "total": total}
        res = await asyncio.to_thread(boost_module.thread_boost, invite, amount, months, nickname)
        return {"status": "done", "successful": len(boost_module.variables.success_tokens)*2, "failed": len(boost_module.variables.failed_tokens)*2}

    res = await _run()
    if res.get("status") == "done":
        msg = f"부스트 완료: 성공 {res.get('successful')} / 실패 {res.get('failed')}"
    else:
        msg = f"부스트 실패: {res.get('reason')} (유효: {res.get('valid')}/{res.get('total')})"

    try:
        await interaction.followup.send(msg)
    except Exception:
        await interaction.response.send_message(msg, ephemeral=True)

# ------------------ 슬래시 명령: /재고_추가하기 (Container UI로 결과 표시) ------------------
@bot.tree.command(name="재고_추가하기", description="토큰을 재고에 추가합니다. (관리자 전용)")
@discord.app_commands.describe(months="기간: 1 또는 3 (월)", tokens_text="토큰 목록(멀티라인, 선택)", tokens_file="토큰 파일 첨부(선택)")
async def slash_add_stock(interaction: discord.Interaction, months: int, tokens_text: str = None, tokens_file: discord.Attachment = None):
    # 권한 체크
    member = interaction.user
    if not isinstance(member, discord.Member) and interaction.guild:
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

    await interaction.response.send_message("토큰 접수 완료. 검사 중입니다...", ephemeral=True)

    # 토큰 수집
    tokens = []
    if tokens_text:
        for line in tokens_text.splitlines():
            line = line.strip()
            if not line:
                continue
            tokens.append(line.split(":")[-1].strip() if ":" in line else line)
    if tokens_file:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(tokens_file.url) as resp:
                    content = await resp.text()
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                tokens.append(line.split(":")[-1].strip() if ":" in line else line)
        except Exception:
            pass

    # 검사 및 파일 추가(병렬화 없이 순차, 안정성 우선)
    def check_and_add_sync(tokens_list):
        filename = "input/1m_tokens.txt" if months == 1 else "input/3m_tokens.txt"
        valid_tokens = []
        invalid_count = 0
        for idx, tok in enumerate(tokens_list, start=1):
            ok = boost_module.check_discord_token(tok, use_proxy=True, thread=idx)
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
        try:
            boost_module.log_stock("add", months, len(valid_tokens), invalid_count, detail="source:slash")
        except Exception:
            pass
        return len(valid_tokens), invalid_count

    valid_cnt, invalid_cnt = await asyncio.to_thread(check_and_add_sync, tokens)

    # Container 레이아웃 생성 및 전송
    layout = StockLayout(valid_cnt, invalid_cnt)
    try:
        # interaction.followup.send를 사용하여 공개 메시지로 전송
        await interaction.followup.send(view=layout)
    except Exception:
        try:
            await interaction.channel.send(view=layout)
        except Exception:
            # 최후 대응: 간단 텍스트 전송
            await interaction.followup.send(f"유효: {valid_cnt}개 / 무효: {invalid_cnt}개")

# ------------------ 슬래시 명령: /재고_표시하기 (60초 갱신) ------------------
@bot.tree.command(name="재고_표시하기", description="현재 재고를 Container UI로 표시하고 60초마다 갱신합니다. (관리자 전용)")
async def slash_show_stock(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) and interaction.guild:
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = interaction.user

    if not is_admin_member(member):
        await interaction.response.send_message("권한이 없습니다. 관리자 역할이 필요합니다.", ephemeral=True)
        return

    await interaction.response.send_message("재고 표시 생성 중...", ephemeral=True)

    def get_counts():
        c1 = len(boost_module.get_all_tokens("input/1m_tokens.txt")) if os.path.exists("input/1m_tokens.txt") else 0
        c3 = len(boost_module.get_all_tokens("input/3m_tokens.txt")) if os.path.exists("input/3m_tokens.txt") else 0
        return c1, c3

    c1, c3 = get_counts()
    # 1개월/3개월을 각각 유효/무효 칸에 배치(레이아웃 제약으로)
    layout = StockLayout(c1, c3)

    try:
        sent = await interaction.channel.send(view=layout)
    except Exception:
        sent = await interaction.followup.send(view=layout)

    async def refresh_loop(message, layout_obj):
        try:
            while True:
                await asyncio.sleep(60)
                nc1, nc3 = get_counts()
                layout_obj.update(nc1, nc3)
                try:
                    await message.edit(view=layout_obj)
                except Exception:
                    break
        finally:
            _inventory_refresh_tasks.pop(message.id, None)

    # 기존 태스크가 있으면 취소 후 교체
    old = _inventory_refresh_tasks.get(sent.id)
    if old and not old.done():
        old.cancel()
    task = asyncio.create_task(refresh_loop(sent, layout))
    _inventory_refresh_tasks[sent.id] = task

    # 결과 링크 알림
    try:
        await interaction.user.send(f"재고 표시가 생성되었습니다: {sent.jump_url}")
    except Exception:
        try:
            await interaction.channel.send(f"재고 표시가 생성되었습니다: {sent.jump_url}")
        except Exception:
            pass

# 봇 시작/동기화
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        await bot.tree.sync()
    except Exception as e:
        print("tree sync error:", e)

if __name__ == "__main__":
    TOK = os.environ.get("DISCORD_BOT_TOKEN")
    if not TOK:
        print("환경변수 DISCORD_BOT_TOKEN 설정 필요")
        exit(1)
    bot.run(TOK)
