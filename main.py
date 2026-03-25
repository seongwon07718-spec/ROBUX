import sqlite3
import discord
from discord import ui

class RobuxMenu(ui.LayoutView):
    def __init__(self):
        super().__init__()
        # 메인 컨테이너 설정
        self.container = ui.Container()
        self.container.accent_color = 0xffffff
        
        self.container.add_item(ui.TextDisplay("## 🛒 구매하기"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.container.add_item(ui.TextDisplay("아래 버튼을 눌러 이용해주세요"))
        self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 버튼 정의
        buy = ui.Button(label="공지", emoji="<:emoji_16:1486337864953495743>")
        buy.callback = self.buy_callback
        
        shop = ui.Button(label="제품", emoji="<:emoji_13:1486337836796874905>")
        shop.callback = self.shop_callback
        
        chage = ui.Button(label="충전", emoji="<:emoji_14:1486337849367330857>", custom_id="charge")
        chage.callback = self.main_callback
        
        info = ui.Button(label="정보", emoji="<:emoji_13:1486337822989484212>")
        info.callback = self.info_callback
        
        # 버튼들을 ActionRow에 담아 추가
        self.container.add_item(ui.ActionRow(buy, shop, chage, info))
        self.add_item(self.container)

    # 에러 방지를 위해 콜백들 정의
    async def buy_callback(self, it: discord.Interaction):
        await it.response.send_message("공지사항 준비 중", ephemeral=True)
    
    async def shop_callback(self, it: discord.Interaction):
        await it.response.send_message("제품 목록 준비 중", ephemeral=True)

    async def info_callback(self, it: discord.Interaction):
        """해외 V2 스타일 프로필 적용 버전 (에러 해결)"""
        
        # 1. DB 데이터 조회 (robux_shop.db)
        u_id = str(it.user.id)
        money = 0
        try:
            conn = sqlite3.connect('robux_shop.db')
            cur = conn.cursor()
            cur.execute("SELECT balance FROM users WHERE user_id = ?", (u_id,))
            row = cur.fetchone()
            conn.close()
            if row: money = row[0]
        except: pass

        # 역할 등급 (최상위 역할)
        roles = [role.name for role in it.user.roles if role.name != "@everyone"]
        role_grade = roles[-1] if roles else "Guest"

        # 2. 정보 컨테이너 생성
        con = ui.Container()
        con.accent_color = 0xffffff

        # [해외 방식] TextDisplay의 'icon_url'을 사용하여 우측 상단 프로필 구현
        # 만약 icon_url도 에러가 난다면, TextDisplay의 텍스트 앞에 이모지를 붙이는 것이 가장 안전합니다.
        con.add_item(ui.TextDisplay(
            f"## {it.user.display_name} 님의 정보",
            icon_url=it.user.display_avatar.url # 해외에서 TextDisplay 우측 상단 아이콘으로 쓰는 방식
        ))
        
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        info_text = (
            f"> <:dot_white:1482000567562928271> **보유 잔액:** `{money:,}` 원\n"
            f"> <:dot_white:1482000567562928271> **사용 금액:** `0` 원\n"
            f"> <:dot_white:1482000567562928271> **역할 등급:** `{role_grade}`\n"
            f"> <:dot_white:1482000567562928271> **할인 혜택:** `0%`"
        )
        con.add_item(ui.TextDisplay(info_text))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # 선택 메뉴
        selecao = ui.Select(placeholder="조회할 내역 선택", options=[
            discord.SelectOption(label="최근 충전 내역", value="charge", emoji="💳"),
            discord.SelectOption(label="최근 구매 내역", value="purchase", emoji="🛒")
        ])
        
        async def res_cb(i: discord.Interaction):
            await i.response.send_message(f"{selecao.values[0]} 내역이 없습니다.", ephemeral=True)
        selecao.callback = res_cb
        
        con.add_item(ui.ActionRow(selecao))

        # 최종 전송 (LayoutView에 con 하나만 넣기)
        await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

    async def main_callback(self, it: discord.Interaction):
        cid = it.data.get('custom_id')
        if cid == "charge":
            con = ui.Container()
            con.accent_color = 0xffffff
            con.add_item(ui.TextDisplay("## 충전 수단 선택\n방식을 선택해주세요."))
            
            btn_bank = ui.Button(label="계좌이체", style=discord.ButtonStyle.gray)
            async def bank_cb(i: discord.Interaction):
                # ChargeModal 클래스 정의 필요
                await i.response.send_modal(ChargeModal())
            btn_bank.callback = bank_cb
            
            con.add_item(ui.ActionRow(btn_bank))
            # 에러 해결: .add_item(con).add_item(btn_bank) 처럼 중복 호출 금지
            await it.response.send_message(view=ui.LayoutView().add_item(con), ephemeral=True)

