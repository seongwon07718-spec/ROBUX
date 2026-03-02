import sqlite3
import discord
from discord import ui
from cultureland import Cultureland, Pin

CULTURE_COOKIE = "여기에_쿠키값을_넣으세요"

async def do_culture_charge(pin_string):
    try:
        cl = Cultureland()
        await cl.login(CULTURE_COOKIE)
        target_pin = Pin(pin_string) 
        result = await cl.charge([target_pin]) 
        
        if isinstance(result, list):
            res = result[0]
            return {"status": "success", "amount": res.amount, "message": res.message}
        else:
            return {"status": "success", "amount": result.amount, "message": result.message}
    except Exception as e:
        print(f"❌ [컬쳐랜드 에러]: {e}")
        return {"status": "error", "message": str(e)}

class CultureModal(ui.Modal, title="문상 실시간 자동 충전"):
    pin = ui.TextInput(
        label="핀번호 입력", 
        placeholder="하이픈(-) 없이 숫자만 입력하세요",
        min_length=16,
        max_length=19
    )

    def __init__(self, bot, log_channel_id):
        super().__init__()
        self.bot = bot
        self.log_channel_id = log_channel_id

    async def on_submit(self, it: discord.Interaction):
        # 진행 중 컨테이너
        wait_con = ui.Container(ui.TextDisplay("## ⏳ 핀번호 확인 중\n\n약 5~10초 정도 소요됩니다. 잠시만 기다려 주세요."), accent_color=0xffff00)
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)
        
        clean_pin = str(self.pin.value).replace("-", "").strip()
        res = await do_culture_charge(clean_pin)    
        
        result_con = ui.Container()
        
        if res["status"] == "success" and res.get("amount", 0) > 0:
            amount = res["amount"]
            u_id = str(it.user.id)
            
            conn = sqlite3.connect('vending1.db')
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (u_id,))
            cur.execute("UPDATE users SET money = money + ?, total_spent = total_spent + ? WHERE user_id = ?", (amount, amount, u_id))
            conn.commit()
            conn.close()
            
            # 성공 컨테이너
            result_con.accent_color = 0x00ff00
            result_con.add_item(ui.TextDisplay(f"## ✅ 충전 성공\n\n**충전 금액:** {amount:,}원\n\n잔액이 정상적으로 반영되었습니다."))
            
            # 로그 전송
            log_chan = self.bot.get_channel(self.log_channel_id)
            if log_chan:
                log_con = ui.Container(ui.TextDisplay(f"## 🎫 문상 자동충전 로그\n\n**신청자:** {it.user.mention}\n**충전금액:** {amount:,}원\n**상태:** 자동 승인 완료"), accent_color=0x00ff00)
                await log_chan.send(view=ui.LayoutView().add_item(log_con))
        else:
            # 실패 컨테이너
            reason = res.get("message", "잘못된 핀번호이거나 이미 사용된 번호입니다.")
            result_con.accent_color = 0xff0000
            result_con.add_item(ui.TextDisplay(f"## ❌ 충전 실패\n\n**사유:** {reason}"))

        await it.edit_original_response(view=ui.LayoutView().add_item(result_con))
