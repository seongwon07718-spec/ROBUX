# --- [ 기존 PurchaseModal 및 데이터 분리 에러 해결 버전 ] ---
class PurchaseModal(ui.Modal):
    def __init__(self, prod_name, price, stock):
        super().__init__(title=f"{prod_name} 구매")
        self.prod_name, self.price, self.stock = prod_name, price, stock
        self.count = ui.TextInput(label="구매 수량", placeholder=f"재고: {stock}개", min_length=1, max_length=5)
        self.add_item(self.count)

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            err_con = ui.Container(ui.TextDisplay("## ❌ 입력 오류"), accent_color=0xff0000)
            err_con.add_item(ui.TextDisplay("숫자로만 입력해주세요.")); return await it.response.send_message(view=ui.LayoutView().add_item(err_con), ephemeral=True)
        
        buy_count = int(self.count.value)
        total_price = self.price * buy_count
        u_id = str(it.user.id)

        wait_con = ui.Container(ui.TextDisplay("## 🛒 구매 처리 중"), accent_color=0xffff00)
        wait_con.add_item(ui.TextDisplay(f"**{self.prod_name}** {buy_count}개 결제를 진행 중입니다..."))
        await it.response.send_message(view=ui.LayoutView().add_item(wait_con), ephemeral=True)

        await asyncio.sleep(1) 
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT money FROM users WHERE user_id = ?", (u_id,))
        row = cur.fetchone(); user_money = row[0] if row else 0

        res_con = ui.Container()
        if buy_count > self.stock:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## ❌ 재고 부족"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        
        if user_money < total_price:
            res_con.accent_color = 0xff0000; res_con.add_item(ui.TextDisplay("## ❌ 잔액 부족"))
            return await it.edit_original_response(view=ui.LayoutView().add_item(res_con))

        cur.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_price, u_id))
        cur.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (buy_count, self.prod_name))
        conn.commit(); conn.close()

        res_con.accent_color = 0x00ff00; res_con.add_item(ui.TextDisplay("## 🎉 구매 완료"))
        res_con.add_item(ui.TextDisplay(f"제품: **{self.prod_name}**\n수량: **{buy_count}개**\n차감: **{total_price:,}원**"))
        await it.edit_original_response(view=ui.LayoutView().add_item(res_con))
        try:
            dm_con = ui.Container(ui.TextDisplay(f"## 📦 구매 영수증"), accent_color=0x00ff00)
            dm_con.add_item(ui.TextDisplay(f"제품: {self.prod_name}\n수량: {buy_count}개\n금액: {total_price:,}원"))
            await it.user.send(view=ui.LayoutView().add_item(dm_con))
        except: pass

# --- [ 신규 추가: 업데이트 공지 명령어 ] ---
@bot.tree.command(name="업데이트_공지", description="서버에 업데이트 공지를 컨테이너로 전송합니다")
@app_commands.describe(내용="공지할 내용을 입력하세요", 채널="공지를 전송할 채널을 선택하세요")
async def update_notice(it: discord.Interaction, 내용: str, 채널: discord.TextChannel):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("관리자만 사용 가능합니다.", ephemeral=True)

    # 공지 컨테이너 디자인
    notice_con = ui.Container(ui.TextDisplay("## 📢 업데이트 안내"), accent_color=0x3498db) # 파란색 계열
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    # 줄바꿈 처리 (\n 입력 시 실제 줄바꿈이 되도록)
    processed_content = 내용.replace("\\n", "\n")
    notice_con.add_item(ui.TextDisplay(processed_content))
    
    notice_con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
    notice_con.add_item(ui.TextDisplay(f"-# 작성자: {it.user.display_name} | 일시: {time.strftime('%Y-%m-%d %H:%M')}"))

    try:
        await 채널.send(view=ui.LayoutView().add_item(notice_con))
        await it.response.send_message(f"✅ {채널.mention} 채널에 공지를 전송했습니다.", ephemeral=True)
    except Exception as e:
        await it.response.send_message(f"❌ 공지 전송 실패: {e}", ephemeral=True)

# --- [ MeuLayout 내 에러 지점 수정 (split 문제 해결) ] ---
# (MeuLayout 클래스 내 buy_callback 중 cat_callback 내부 수정)
# ... 중략 ...
            async def prod_callback(it3: discord.Interaction):
                # split('|')로 통일하여 에러 방지
                raw_data = prod_select.values[0]
                p_name, p_price, p_stock = raw_data.split('|') 
                await it3.response.send_modal(PurchaseModal(p_name, int(p_price), int(p_stock)))

            prod_select.callback = prod_callback
            # 데이터 생성 시에도 '|'로 공백 없이 넣기 (511번 라인 대응)
            prod_options = [discord.SelectOption(label=f"{p[0]}ㅣ{p[1]:,}원", value=f"{p[0]}|{p[1]}|{p[2]}") for p in prods]
# ... 후략 ...
