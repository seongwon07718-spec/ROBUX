import discord
from discord.ext import commands
from discord import app_commands
import os
import requests
import json
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Discord 봇 토큰 및 API 엔드포인트 로드
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TOPUP_API_ENDPOINT = os.getenv("TOPUP_API_ENDPOINT") # ⚠️ 이 값은 iCloud 단축어 분석 후 실제 API URL로 설정해야 합니다!
YOUR_CUSTOM_API_KEY = os.getenv("YOUR_CUSTOM_API_KEY") # ⚠️ 필요한 경우 iCloud 단축어에서 찾은 API Key (없으면 삭제)

# 봇 권한 설정 (Intents)
intents = discord.Intents.default()
intents.message_content = True # 메시지 콘텐츠를 읽기 위함
intents.members = True # 멤버 정보 접근 위함 (역할 부여 등에 필요)

# 봇 인스턴스 생성
bot = commands.Bot(command_prefix='!', intents=intents)

# -----------------------------------------------------------
# 1. 충전 정보 입력 모달 (Modal) 클래스
# -----------------------------------------------------------
class TopUpModal(discord.ui.Modal, title="충전 정보 입력"):
    def __init__(self, modal_id: str):
        super().__init__(custom_id=modal_id)

    # 입금자명 입력 필드
    depositor_name = discord.ui.TextInput(
        label="입금자명",
        placeholder="예: 홍길동",
        max_length=50,
        required=True
    )

    # 충전 금액 입력 필드
    amount = discord.ui.TextInput(
        label="충전 금액 (원)",
        placeholder="예: 10000",
        max_length=10,
        required=True,
        style=discord.TextStyle.short
    )

    # 모달 제출 시 호출되는 함수
    async def on_submit(self, interaction: discord.Interaction):
        입금자명 = self.depositor_name.value
        충전금액_str = self.amount.value

        # 금액이 숫자인지 먼저 검증
        if not 충전금액_str.isdigit():
            await interaction.response.send_message("❌ 충전 금액은 숫자로만 입력해주세요.", ephemeral=True)
            return
        
        충전금액 = int(충전금액_str)

        # 사용자에게 API 호출 처리 중임을 알리는 임시 메시지 전송
        await interaction.response.send_message(
            f"✅ 입금자명: `{입금자명}`, 충전 금액: `{충전금액}원` 정보 확인 및 처리 중...", 
            ephemeral=True
        )

        try:
            # ⚠️ 여기부터 iCloud 단축어 분석을 통해 얻은 API 정보를 바탕으로 수정해야 합니다.
            # ----------------------------------------------------------------------------------------------------------------------
            # 예시: 단축어가 POST 요청으로 JSON 데이터를 보내는 경우
            # iCloud 단축어의 'URL 콘텐츠 가져오기' 액션에서 다음 정보들을 확인하여 수정하세요.
            # - URL (-> TOPUP_API_ENDPOINT 변수)
            # - 메서드 (GET/POST 등)
            # - 요청 본문 (JSON / Form Data)의 키(Key)와 값(Value) 구조
            # - 헤더 (Authorization, Content-Type 등)
            # ----------------------------------------------------------------------------------------------------------------------

            headers = {
                "Content-Type": "application/json", # 일반적으로 JSON 데이터 전송 시 사용
                # "Authorization": f"Bearer {YOUR_CUSTOM_API_KEY}" # ⚠️ API 키가 필요한 경우 주석 해제 후 YOUR_CUSTOM_API_KEY 사용
            }
            
            payload = {
                "depositor_name": 입금자명, # ⚠️ 단축어가 사용하는 실제 Key 이름으로 변경 (예: "name", "payer")
                "amount": 충전금액,       # ⚠️ 단축어가 사용하는 실제 Key 이름으로 변경 (예: "charge_amount", "money")
                "discord_user_id": str(interaction.user.id), # 충전 요청한 디스코드 사용자 ID (필요 시)
                "discord_username": interaction.user.name, # 충전 요청한 디스코드 사용자 이름 (필요 시)
                # ⚠️ 단축어가 요구하는 추가 데이터가 있다면 여기에 추가 (예: "product_id": "ABC123")
            }

            # 실제 API 호출
            response = requests.post(
                TOPUP_API_ENDPOINT, # .env 파일에서 로드된 엔드포인트 사용
                headers=headers, 
                data=json.dumps(payload), # payload를 JSON 문자열로 변환
                timeout=10 # 요청 타임아웃 설정 (10초)
            )
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생 (4xx, 5xx)

            response_data = response.json() # API 응답이 JSON 형식이라고 가정

            # ⚠️ API 응답에 따라 성공/실패 여부를 판단하는 로직을 수정해야 합니다.
            # ----------------------------------------------------------------------------------------------------------------------
            # 예시: 응답 데이터에 'status' 키가 'success'일 경우 성공으로 간주
            if response_data.get("status") == "success":
                await interaction.followup.send( # followup.send: 이전 메시지 이후 추가 메시지 전송
                    f"🎉 `{interaction.user.display_name}`님, **{충전금액}원** 충전이 성공적으로 처리되었습니다! ",
                    ephemeral=False # 채널의 모든 사용자가 볼 수 있도록
                )
            else:
                error_message_from_api = response_data.get("message", "API로부터 알 수 없는 오류가 발생했습니다.")
                await interaction.followup.send(
                    f"❌ 충전 처리 중 오류가 발생했습니다: {error_message_from_api}",
                    ephemeral=True
                )
            # ----------------------------------------------------------------------------------------------------------------------

        except requests.exceptions.Timeout:
            await interaction.followup.send(
                "⚠️ API 응답 시간이 너무 오래 걸립니다. 다시 시도해주세요.", 
                ephemeral=True
            )
        except requests.exceptions.RequestException as e:
            # 네트워크 오류, HTTP 오류 (4xx, 5xx) 등을 포함
            print(f"API 호출 중 오류 발생: {e}")
            await interaction.followup.send(
                f"⚠️ 서버 통신 중 문제가 발생했습니다: `{e}`. 잠시 후 다시 시도해주세요.", 
                ephemeral=True
            )
        except json.JSONDecodeError:
            print("API 응답이 유효한 JSON 형식이 아닙니다.")
            await interaction.followup.send(
                "⚠️ API 응답 형식이 올바르지 않습니다. 관리자에게 문의해주세요.", 
                ephemeral=True
            )
        except Exception as e:
            # 기타 예상치 못한 오류 처리
            print(f"충전 처리 중 예상치 못한 오류: {e}")
            await interaction.followup.send(
                f"❌ 충전 처리 중 심각한 오류가 발생했습니다. 관리자에게 문의해주세요. 오류코드: `{e}`", 
                ephemeral=True
            )

# -----------------------------------------------------------
# 2. '충전' 버튼이 포함된 View 클래스
# -----------------------------------------------------------
class TopUpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) # 3분 동안 유효

    @discord.ui.button(label="충전하기", style=discord.ButtonStyle.primary, emoji="💰")
    async def topup_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 버튼이 눌리면 TopUpModal을 사용자에게 표시합니다.
        await interaction.response.send_modal(TopUpModal(modal_id=f"topup_modal_{interaction.user.id}"))

# -----------------------------------------------------------
# 3. 봇 이벤트 핸들러
# -----------------------------------------------------------
@bot.event
async def on_ready():
    print(f'로그인되었습니다! 봇 이름: {bot.user.name}, ID: {bot.user.id}')
    try:
        # 슬래시 명령어 동기화
        synced = await bot.tree.sync()
        print(f"동기화된 슬래시 명령어 수: {len(synced)}개")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")

# -----------------------------------------------------------
# 4. 슬래시 명령어: /충전
# -----------------------------------------------------------
@bot.tree.command(name="충전", description="자동 충전 안내 메시지와 버튼을 표시합니다.")
async def show_topup_interface(interaction: discord.Interaction):
    # 충전 안내 임베드 생성
    embed = discord.Embed(
        title="✨ 디스코드 계정 자동 충전 시스템 ✨",
        description=(
            "아래 '충전하기' 버튼을 눌러 계정을 충전할 수 있습니다.\n"
            "정확한 입금자명과 충전 금액을 입력해주세요."
        ),
        color=discord.Color.blue()
    )
    embed.add_field(name="🚨 중요 안내", value="입력하신 정보가 정확해야만 충전이 정상적으로 처리됩니다.", inline=False)
    
    # 봇의 아바타를 썸네일로 설정 (선택 사항)
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    
    # 임베드와 View(버튼 포함)를 함께 전송
    await interaction.response.send_message(embed=embed, view=TopUpView(), ephemeral=False)

# 봇 실행
if DISCORD_BOT_TOKEN:
    bot.run(DISCORD_BOT_TOKEN)
else:
    print("오류: DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
