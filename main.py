from disnake import ui, PartialEmoji, ButtonStyle, SeparatorSpacing, Interaction
from disnake.ext import commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 커스텀 이모지 (서버에 실제 존재하는 이모지 ID로 변경하세요)
custom_emojis1 = PartialEmoji(name="send", id=1439222645035106436)
custom_emojis2 = PartialEmoji(name="charge", id=1439222646641262706)
custom_emojis3 = PartialEmoji(name="info", id=1439222648512053319)


class ServiceContainerView(ui.LayoutView):
    def __init__(self, stock_display: str, kimchi_premium_display: str):
        super().__init__(timeout=None)  # 퍼시스턴트 뷰

        container = ui.Container()  # 단일 컨테이너 생성
        
        # 텍스트 아이템 추가
        container.add_item(ui.TextDisplay("**BTCC | 코인대행**"))
        container.add_item(ui.TextDisplay("아래 버튼을 눌러 이용해주세요"))
        container.add_item(ui.Separator(spacing=SeparatorSpacing.small))

        # 재고/김프 상태 표시 (비활성화 버튼)
        container.add_item(ui.Button(label=f"실시간 재고: {stock_display}", style=ButtonStyle.grey, disabled=True))
        container.add_item(ui.Button(label=f"실시간 김프: {kimchi_premium_display}", style=ButtonStyle.grey, disabled=True))
        container.add_item(ui.Separator(spacing=SeparatorSpacing.small))

        # 핵심 버튼 3개 생성
        send_btn = ui.Button(label="송금", style=ButtonStyle.grey, emoji=custom_emojis1, custom_id="use_service_button")
        info_btn = ui.Button(label="정보 보기", style=ButtonStyle.grey, emoji=custom_emojis3, custom_id="my_info_button")
        charge_btn = ui.Button(label="충전", style=ButtonStyle.grey, emoji=custom_emojis2, custom_id="charge_button")

        container.add_item(send_btn)
        container.add_item(info_btn)
        container.add_item(charge_btn)
        container.add_item(ui.Separator(spacing=SeparatorSpacing.small))

        # 하단 팁 텍스트
        container.add_item(ui.TextDisplay("Tip : 송금 내역은 정보 보기 버튼을 통해 볼 수 있습니다."))

        # 컨테이너를 뷰에 추가
        self.add_item(container)

        # 버튼 콜백 등록
        send_btn.callback = self.send_callback
        info_btn.callback = self.info_callback
        charge_btn.callback = self.charge_callback

    async def send_callback(self, interaction: Interaction):
        logger.info(f"{interaction.user} 님이 송금 버튼을 클릭했습니다.")
        await interaction.response.send_message("송금 기능을 실행합니다.", ephemeral=True)

    async def info_callback(self, interaction: Interaction):
        logger.info(f"{interaction.user} 님이 정보 보기 버튼을 클릭했습니다.")
        await interaction.response.send_message("내 정보 기능을 실행합니다.", ephemeral=True)

    async def charge_callback(self, interaction: Interaction):
        logger.info(f"{interaction.user} 님이 충전 버튼을 클릭했습니다.")
        await interaction.response.send_message("충전 기능을 실행합니다.", ephemeral=True)


# 봇 생성 및 명령어 등록 예시 (기본 셋업)
bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all())

@bot.slash_command(name="show_service_ui", description="서비스 컨테이너 UI를 띄웁니다.")
async def show_service_ui(inter):
    # 실시간 재고 및 김프 예시 값
    stock_display_value = "500.00 USDT"
    kimchi_premium_value = "3.45%"

    view = ServiceContainerView(stock_display_value, kimchi_premium_value)
    await inter.response.send_message("대행 서비스 UI입니다.", view=view, ephemeral=True)


if __name__ == "__main__":
    TOKEN = "YOUR_BOT_TOKEN"  # 봇 토큰으로 바꿔주세요
    bot.run(TOKEN)
