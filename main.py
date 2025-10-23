# main.py (최종본) — 컨테이너 내부 Thumbnail / MediaGallery 사용, attachment 방식, 폴백 포함
import discord
from discord import PartialEmoji, ui, app_commands
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

IMAGE_PATH = "imagens/disco.png"  # 이미지 파일 경로 (프로젝트 기준)

# --- Helper: 안전하게 Thumbnail / MediaGallery 존재 여부 체크 ---
_supports_thumbnail = hasattr(ui, "Thumbnail")
_supports_mediagallery = hasattr(ui, "MediaGallery")

class MyLayoutVending(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        
        # 메인 컨테이너 생성
        self.c = ui.Container(ui.TextDisplay("24시간 OTT 자판기\n-# 버튼을 눌러 이용해주세요 !"))
        self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Thumbnail / MediaGallery 추가(지원 시)
        if _supports_thumbnail:
            try:
                # Thumbnail을 accessory로 넣은 Section
                thumb = ui.Thumbnail("attachment://disco.png")
                sessao = ui.Section(ui.TextDisplay(""), accessory=thumb)
                self.c.add_item(sessao)
                self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            except Exception:
                # 실패하면 빈 라인으로 대체
                self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        else:
            # Thumbnail 미지원 환경: 텍스트로 대체 안내(이미지는 panel_vending에서 전송됨)
            self.c.add_item(ui.TextDisplay("이미지 미리보기는 클라이언트 버전에 따라 표시되지 않을 수 있습니다."))
            self.c.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # MediaGallery: 여러 이미지를 보여줄 때 사용 (지원 시 빈 갤러리 추가; runtime에서 media 항목을 추가)
        if _supports_mediagallery:
            try:
                galeria = ui.MediaGallery()
                # 실제 media 항목은 panel_vending에서 추가 (attachment://disco.png)
                self.c.add_item(galeria)
            except Exception:
                pass

        # 이모지 생성 (기존 사용하던 커스텀 이모지 유지)
        charge_emoji = PartialEmoji.from_str("<:3_:1426934636428394678>")
        notification_emoji = PartialEmoji.from_str("<:6_:1426943544928505886>")
        info_emoji = PartialEmoji.from_str("<:5_:1426936503635939428>")
        purchase_emoji = PartialEmoji.from_str("<:4_:1426936460149395598>")
        
        # 버튼 생성 및 이모지 추가
        button_1 = ui.Button(label="충전", custom_id="charge_button", emoji=charge_emoji)
        button_2 = ui.Button(label="알림", custom_id="notification_button", emoji=notification_emoji)
        button_3 = ui.Button(label="정보", custom_id="my_info_button", emoji=info_emoji)
        button_4 = ui.Button(label="구매", custom_id="purchase_button", emoji=purchase_emoji)
        
        # 버튼 행 생성
        linha = ui.ActionRow(button_1, button_2)
        linha2 = ui.ActionRow(button_3, button_4)
        
        # 컨테이너에 버튼 행 추가
        self.c.add_item(linha)
        self.c.add_item(linha2)
        
        # 뷰에 컨테이너 추가
        self.add_item(self.c)

# ---------------- panel_vending: attachment 방식으로 파일과 view 동시 전송 ----------------
@bot.tree.command(name="자판기패널", description="자판기 패널을 표시합니다")
@app_commands.checks.has_permissions(administrator=True)
async def panel_vending(interaction: discord.Interaction):
    layout = MyLayoutVending()
    
    if not os.path.isfile(IMAGE_PATH):
        await interaction.response.send_message("이미지 파일을 찾을 수 없습니다. 'imagens/disco.png' 경로를 확인하세요.", ephemeral=True)
        return

    file = discord.File(IMAGE_PATH, filename="disco.png")
    
    if _supports_mediagallery or _supports_thumbnail:
        try:
            for item in getattr(layout, "children", []):
                try:
                    inner_children = getattr(item, "children", []) or []
                except Exception:
                    inner_children = []
                for sub in inner_children:
                    
                    if _supports_mediagallery and getattr(sub, "__class__", None).__name__ == "MediaGallery":
                        try:
                            sub.add_item(media="attachment://disco.png")
                        except Exception:
                            pass
        except Exception:
            pass

    await interaction.response.send_message(file=file, view=layout, ephemeral=False)

# ---------------- on_ready ----------------
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}개의 슬래시 명령이 동기화되었습니다.")
    except Exception as e:
        print("명령 동기화 오류:", e)
    print(f"{bot.user}로 로그인했습니다.")

bot.run("")
