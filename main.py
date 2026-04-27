import asyncio
import time
import uuid
import re
import discord
from discord.ext import commands
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# ─── 수정 가능한 은행 정보 ────────────────────────────────
BANK_NAME = "국민은행"
BANK_ACCOUNT = "000000-00-000000"
BANK_OWNER = "홍길동"
# ─────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
app = FastAPI()

# 대기 중인 입금 목록
pending_deposits = {}


# ─── 충전 완료 처리 함수 ──────────────────────────────────
async def confirm_deposit(name: str, amount: str):
    matched_id = None
    for deposit_id, data in pending_deposits.items():
        if data["name"] == name and data["amount"].replace(",", "") == amount.replace(",", ""):
            matched_id = deposit_id
            break

    if matched_id is None:
        return False

    data = pending_deposits.pop(matched_id)
    message = data["message"]

    class SuccessContainer(discord.ui.Container):
        text = discord.ui.TextDisplay("## ✅ 충전 완료")
        sep = discord.ui.Separator()
        text2 = discord.ui.TextDisplay(
            f"**입금자명:** {name}\n"
            f"**충전 금액:** {amount}원\n\n"
            "충전이 완료되었습니다. 감사합니다! 🎉"
        )

    class SuccessLayout(discord.ui.LayoutView):
        container = SuccessContainer(accent_color=0x57f287)

    await message.edit(view=SuccessLayout())
    return True


# ─── FastAPI /deposit 엔드포인트 ──────────────────────────
@app.post("/deposit")
async def deposit(request: Request):
    data = await request.json()
    message_text = data.get("message", "")

    amount_match = re.search(r"입금\s*([\d,]+)원", message_text)
    name_match = re.search(r"입금\s*[\d,]+원\n(.+)", message_text)

    if not name_match or not amount_match:
        return JSONResponse({"status": "fail", "reason": "파싱 실패"}, status_code=400)

    name = name_match.group(1).strip()
    amount = amount_match.group(1).replace(",", "")

    result = await confirm_deposit(name, amount)

    if result:
        return JSONResponse({"status": "success", "name": name, "amount": amount})
    else:
        return JSONResponse({"status": "fail", "reason": "일치하는 입금 신청 없음"}, status_code=404)


# ─── 입금 모달 ───────────────────────────────────────────
class DepositModal(discord.ui.Modal, title="계좌이체 충전"):
    name = discord.ui.TextInput(
        label="입금자명",
        placeholder="입금자명을 입력하세요",
        required=True
    )
    amount = discord.ui.TextInput(
        label="충전할 금액",
        placeholder="예) 10000",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        expires_timestamp = int(time.time()) + (5 * 60)
        deposit_id = str(uuid.uuid4())

        class BankContainer(discord.ui.Container):
            text = discord.ui.TextDisplay("## 계좌 정보")
            sep = discord.ui.Separator()
            text2 = discord.ui.TextDisplay(
                f"**입금자명:** {self.name.value}\n"
                f"**충전 금액:** {self.amount.value}원\n"
            )
            sep2 = discord.ui.Separator()
            text3 = discord.ui.TextDisplay(
                f"**은행명:** `{BANK_NAME}`\n"
                f"**계좌번호:** `{BANK_ACCOUNT}`\n"
                f"**예금주:** `{BANK_OWNER}`\n\n"
                f"**입금 마감: <t:{expires_timestamp}:R>**"
            )

        class BankLayout(discord.ui.LayoutView):
            container = BankContainer(accent_color=0xffffff)

        await interaction.response.send_message(view=BankLayout(), ephemeral=True)
        message = await interaction.original_response()

        pending_deposits[deposit_id] = {
            "name": self.name.value,
            "amount": self.amount.value,
            "message": message
        }

        asyncio.create_task(self.check_timeout(deposit_id, message))

    async def check_timeout(self, deposit_id: str, message):
        await asyncio.sleep(300)

        if deposit_id not in pending_deposits:
            return

        pending_deposits.pop(deposit_id)

        class FailContainer(discord.ui.Container):
            text = discord.ui.TextDisplay("## ❌ 충전 실패")
            sep = discord.ui.Separator()
            text2 = discord.ui.TextDisplay(
                "입금 시간이 초과되었습니다.\n"
                "다시 시도하려면 충전 버튼을 눌러주세요."
            )

        class FailLayout(discord.ui.LayoutView):
            container = FailContainer(accent_color=0xff0000)

        await message.edit(view=FailLayout())


# ─── 충전 방법 선택 컨테이너 ──────────────────────────────
class ChargeContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 💳 충전 방법 선택\n원하는 충전 방법을 선택하세요.")
    sep = discord.ui.Separator(divider=True)
    row = discord.ui.ActionRow()

    @row.button(label="계좌이체", style=discord.ButtonStyle.secondary, custom_id="charge_bank", emoji="🏦")
    async def bank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DepositModal())

    @row.button(label="코인결제", style=discord.ButtonStyle.secondary, custom_id="charge_coin", emoji="🪙")
    async def coin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🪙 **코인결제** 메뉴입니다.", ephemeral=True)


class ChargeLayout(discord.ui.LayoutView):
    container = ChargeContainer(accent_color=0xffffff)


# ─── 메인 패널 컨테이너 ───────────────────────────────────
class PanelContainer(discord.ui.Container):
    text = discord.ui.TextDisplay("## 구매하기\n원하는 항목을 선택하세요")
    sep = discord.ui.Separator(divider=True)
    image = discord.ui.MediaGallery(
        discord.MediaGalleryItem(media="https://여기에이미지URL.png")
    )
    sep2 = discord.ui.Separator(divider=True)
    row = discord.ui.ActionRow()

    @row.button(label="구매", style=discord.ButtonStyle.secondary, custom_id="panel_buy", emoji="<:1302328398856847474:1498278220087431188>")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**구매** 메뉴입니다.", ephemeral=True)

    @row.button(label="제품", style=discord.ButtonStyle.secondary, custom_id="panel_product", emoji="<:1302328347765899395:1498278218644324543>")
    async def product_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**제품** 목록입니다.", ephemeral=True)

    @row.button(label="충전", style=discord.ButtonStyle.secondary, custom_id="panel_charge", emoji="<:1302328427545624689:1498278217017196594>")
    async def charge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(view=ChargeLayout(), ephemeral=True)

    @row.button(label="정보", style=discord.ButtonStyle.secondary, custom_id="panel_info", emoji="<:1306285145132892180:1498278215116919029>")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("**정보** 페이지입니다.", ephemeral=True)


class PanelLayout(discord.ui.LayoutView):
    container = PanelContainer(accent_color=0xffffff)


# ─── 봇 이벤트 ───────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user}")


@bot.tree.command(name="panel", description="구매 패널을 표시합니다")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message(view=PanelLayout())


# ─── 봇 + FastAPI 동시 실행 ───────────────────────────────
async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(
        bot.start("YOUR_BOT_TOKEN"),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
