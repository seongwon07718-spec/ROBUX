import discord
from discord import app_commands, ui
from discord.ext import commands
import sqlite3, asyncio, re, uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from threading import Thread
from datetime import datetime

# --- 설정 ---
TOKEN = "YOUR_BOT_TOKEN"
# 실제 입금 받을 계좌 정보
BANK_INFO = "OO은행 123-456-78-90123 (예금주: 홍길동)"

# FastAPI 설정
app = FastAPI()
pending_deposits = {} # 입금 대기 상태 저장소 { "이름_금액": True }

class ChargeData(BaseModel):
    message: str

@app.post("/charge")
async def receive_charge(data: ChargeData):
    msg = data.message.strip()
    # 정규식으로 금액과 이름 추출
    amount_match = re.search(r'입금\s*([\d,]+)원', msg)
    name_match = re.search(r'원\n([가-힣]+)\n잔액', msg)
    
    if amount_match and name_match:
        amount = amount_match.group(1).replace(",", "")
        name = name_match.group(1)
        key = f"{name}_{amount}"
        pending_deposits[key] = True
    else:
        fallback = re.search(r'([가-힣]+)\s*(\d+)', msg)
        if fallback:
            key = f"{fallback.group(1)}_{fallback.group(2)}"
            pending_deposits[key] = True
    return {"ok": True}

# --- 봇 클래스 ---
class RobuxBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        conn = sqlite3.connect('robux_shop.db')
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)")
        conn.commit()
        conn.close()
        await self.tree.sync()

bot = RobuxBot()

# --- 입금 정보 입력 모달 ---
class ChargeModal(ui.Modal, title="계좌이체 충전 신청"):
    depositor = ui.TextInput(label="입금자명", placeholder="입금하실 성함을 입력하세요", min_length=2, max_length=10)
    amount = ui.TextInput(label="충전 금액", placeholder="숫자만 입력하세요 (예: 10000)", min_length=3)

    async def on_submit(self, it: discord.Interaction):
        if not self.amount.value.isdigit():
            return await it.response.send_message("금액은 숫자만 입력 가능합니다.", ephemeral=True)
        
        # 1단계: 애니메이션 시작
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("## ⏳ 충전 준비 중..."))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("🔄 충전 서버 api 연결 중 (1/3)"))
        
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)
        msg = await it.original_response()

        # 단계별 수정 애니메이션
        steps = [
            "✅ 충전 서버 api 연결 완료 (1/3)\n🔄 입금자명/충전금액 설정 중 (2/3)",
            "✅ 입금자명/충전금액 설정 완료 (2/3)\n🔄 안전한 충전을 위한 설정 중 (3/3)",
            "✅ 모든 설정이 완료되었습니다! (3/3)"
        ]

        for step in steps:
            await asyncio.sleep(1.5)
            con.clear_items()
            con.add_item(ui.TextDisplay("## ⏳ 충전 준비 중..."))
            con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            con.add_item(ui.TextDisplay(step))
            await msg.edit(view=ui.LayoutView().add_item(con))

        # 최종 계좌 안내 컨테이너
        await asyncio.sleep(1)
        con.clear_items()
        con.accent_color = 0xFEE75C # 노란색
        con.add_item(ui.TextDisplay(f"## 💳 입금 안내\n\n**계좌번호:** `{BANK_INFO}`\n**입금자명:** `{self.depositor.value}`\n**입금금액:** `{int(self.amount.value):,}원`"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        con.add_item(ui.TextDisplay("⚠️ 입금자명과 금액이 일치해야 자동으로 충전됩니다.\n입금이 확인될 때까지 이 창을 닫지 마세요 (최대 5분 대기)"))
        await msg.edit(view=ui.LayoutView().add_item(con))

        # 자동 충전 대기 로직 (5분간 감지)
        key = f"{self.depositor.value}_{self.amount.value}"
        success = False
        for _ in range(60): # 5초씩 60번 = 300초(5분)
            if pending_deposits.get(key):
                success = True
                del pending_deposits[key] # 처리 후 제거
                break
            await asyncio.sleep(5)

        if success:
            # DB 잔액 추가
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", 
                        (str(it.user.id), int(self.amount.value), int(self.amount.value)))
            conn.commit()
            conn.close()

            con.clear_items()
            con.accent_color = 0x57F287 # 녹색
            con.add_item(ui.TextDisplay(f"## 🎉 충전 완료\n\n<@{it.user.id}> 님의 잔액이 성공적으로 충전되었습니다!\n**충전된 금액:** `{int(self.amount.value):,}원`"))
            await msg.edit(view=ui.LayoutView().add_item(con))
        else:
            con.add_item(ui.TextDisplay("\n❌ **시간 초과:** 입금이 확인되지 않았습니다. 문의가 필요하시면 관리자를 찾아주세요."))
            await msg.edit(view=ui.LayoutView().add_item(con))

# --- 자판기 메뉴 뷰 ---
class RobuxMenu(ui.LayoutView):
    def __init__(self):
        super().__init__()
        con = ui.Container()
        con.accent_color = 0x00AAFF
        con.add_item(ui.TextDisplay("## 🤖 로벅스 자동 자판기"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        row = ui.ActionRow()
        btns = [("📢 공지", "notice"), ("🛒 구매", "buy"), ("💳 충전", "charge"), ("👤 정보", "info")]
        for label, custom_id in btns:
            btn = ui.Button(label=label, custom_id=custom_id, style=discord.ButtonStyle.gray if "charge" not in custom_id else discord.ButtonStyle.blurple)
            btn.callback = self.main_callback
            row.add_item(btn)
        
        con.add_item(row)
        self.add_item(con)

    async def main_callback(self, it: discord.Interaction):
        cid = it.data['custom_id']
        if cid == "charge":
            # 충전 수단 선택 컨테이너
            con = ui.Container()
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 💳 충전 수단 선택\n원하시는 충전 방식을 선택해주세요."))
            
            btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.green, emoji="🏦")
            async def bank_cb(i: discord.Interaction):
                await i.response.send_modal(ChargeModal())
            btn_bank.callback = bank_cb
            
            await it.response.send_message(view=ui.LayoutView().add_item(con).add_item(btn_bank), ephemeral=True)
        else:
            await it.response.send_message(f"{cid} 기능은 준비 중입니다.", ephemeral=True)

# --- 명령어 ---
@bot.tree.command(name="로벅스_자판기", description="로벅스 자판기 메뉴를 불러옵니다")
async def open_vending(it: discord.Interaction):
    await it.response.send_message(view=RobuxMenu())

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=88)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    bot.run(TOKEN)

