import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} 온라인!")

@bot.tree.command(name="panel", description="구매 패널을 표시합니다.")
async def panel(interaction: discord.Interaction):
    # Components V2 - Container 구성
    container = discord.ui.Container(
        discord.ui.TextDisplay("## 🛒 구매 패널\n원하는 항목을 선택하세요."),
        discord.ui.Separator(),
        discord.ui.ActionRow(
            discord.ui.Button(
                label="🛍️ 구매",
                style=discord.ButtonStyle.primary,
                custom_id="panel_buy"
            ),
            discord.ui.Button(
                label="📦 제품",
                style=discord.ButtonStyle.secondary,
                custom_id="panel_product"
            ),
            discord.ui.Button(
                label="💳 충전",
                style=discord.ButtonStyle.success,
                custom_id="panel_charge"
            ),
            discord.ui.Button(
                label="ℹ️ 정보",
                style=discord.ButtonStyle.secondary,
                custom_id="panel_info"
            ),
        )
    )

    await interaction.response.send_message(
        components=[container],
        flags=discord.MessageFlags.is_components_v2
    )

# 버튼 핸들러
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    cid = interaction.data.get("custom_id")

    responses = {
        "panel_buy":     "🛍️ **구매** 메뉴입니다.",
        "panel_product": "📦 **제품** 목록입니다.",
        "panel_charge":  "💳 **충전** 메뉴입니다.",
        "panel_info":    "ℹ️ **정보** 페이지입니다.",
    }

    if cid in responses:
        await interaction.response.send_message(responses[cid], ephemeral=True)

bot.run("YOUR_BOT_TOKEN")
