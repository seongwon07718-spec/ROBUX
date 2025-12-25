import discord
from discord import app_commands, ui
from discord.ext import commands
import sqlite3

# --- 데이터베이스 초기화 ---
db = sqlite3.connect("vending_machine.db")
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, money INTEGER DEFAULT 0, total_pay INTEGER DEFAULT 0, grade TEXT DEFAULT '일반')")
cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS payment_settings (method TEXT PRIMARY KEY, allowed INTEGER DEFAULT 1)")
cur.execute("CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, category TEXT, price INTEGER, stock TEXT, emoji TEXT, cat_emoji TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS logs (type TEXT PRIMARY KEY, channel_id INTEGER)")
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- 유틸리티 함수 ---
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    res = cur.fetchone()
    if not res:
        cur.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        db.commit()
        return (user_id, 0, 0, '일반')
    return res

def get_log_channel(log_type):
    cur.execute("SELECT channel_id FROM logs WHERE type = ?", (log_type,))
    res = cur.fetchone()
    return res[0] if res else None

# --- 모달 클래스 모음 ---

class ReviewModal(ui.Modal, title="후기 작성하기"):
    rating = ui.TextInput(label="별점 (1~5 숫자만)", placeholder="5", min_length=1, max_length=1)
    content = ui.TextInput(label="후기 내용", style=discord.TextStyle.paragraph, placeholder="구매 후기를 작성해주세요.")

    def __init__(self, product_name, amount, price, log_channel_id):
        super().__init__()
        self.product_name = product_name
        self.amount = amount
        self.price = price
        self.log_channel_id = log_channel_id

    async def on_submit(self, interaction: discord.Interaction):
        stars = "⭐" * int(self.rating.value)
        channel = bot.get_channel(self.log_channel_id)
        if not channel: return await interaction.response.send_message("후기 채널을 찾을 수 없습니다.", ephemeral=True)
        
        embed = discord.Embed(color=discord.Color.gold())
        embed.description = f"**제품**\n```{self.product_name}```\n**수량**\n```{self.amount}```\n**금액**\n```{self.price}```\n" \
                            f"ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n\n**유저**\n**{interaction.user.name}**\n\n" \
                            f"**별점**\n**{stars}**\n\n**후기**\n**{self.content.value}**"
        
        await channel.send(embed=embed)
        await interaction.response.send_message("후기가 성공적으로 등록되었습니다!", ephemeral=True)

class ChargeModal(ui.Modal, title="계좌이체 충전 신청"):
    name = ui.TextInput(label="입금자명", placeholder="홍길동")
    amount = ui.TextInput(label="충전 금액", placeholder="5000")

    async def on_submit(self, interaction: discord.Interaction):
        log_ch_id = get_log_channel("충전로그")
        if not log_ch_id: return await interaction.response.send_message("충전 로그 채널이 설정되지 않았습니다.", ephemeral=True)
        
        cur.execute("SELECT value FROM settings WHERE key = 'bank_info'")
        bank_info = cur.fetchone()
        if not bank_info: return await interaction.response.send_message("관리자가 계좌 정보를 설정하지 않았습니다.", ephemeral=True)
        
        owner, bank, num = bank_info[0].split('|')
        
        embed = discord.Embed(color=discord.Color.blue())
        embed.add_field(name="**예금주**", value=f"```{owner}```", inline=False)
        embed.add_field(name="**은행명**", value=f"```{bank}```", inline=False)
        embed.add_field(name="**계좌번호**", value=f"```{num}```", inline=False)
        embed.set_footer(text="5분안에 입금해주셔야 자동충전됩니다\n자동충전 안될 시 관리자한테 문의바랍니다")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_ch = bot.get_channel(log_ch_id)
        log_embed = discord.Embed(color=discord.Color.orange())
        log_embed.add_field(name="**신청 유저**", value=f"```{interaction.user.name} | {interaction.user.id}```", inline=False)
        log_embed.add_field(name="**신청 금액**", value=f"```{self.amount.value}```", inline=True)
        log_embed.add_field(name="**입금자명**", value=f"```{self.name.value}```", inline=True)
        
        await log_ch.send(embed=log_embed, view=ChargeAdminView(interaction.user.id, int(self.amount.value)))

# --- 뷰 클래스 모음 ---

class ChargeAdminView(ui.View):
    def __init__(self, user_id, amount):
        super().__init__(timeout=None)
        self.target_user_id = user_id
        self.amount = amount

    @ui.button(label="허용", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        user_data = get_user(self.target_user_id)
        new_money = user_data[1] + self.amount
        cur.execute("UPDATE users SET money = ?, total_pay = total_pay + ? WHERE id = ?", (new_money, self.amount, self.target_user_id))
        db.commit()
        
        target = await bot.fetch_user(self.target_user_id)
        dm_embed = discord.Embed(color=discord.Color.green())
        dm_embed.add_field(name="**충전 금액**", value=f"```{self.amount}```", inline=False)
        dm_embed.add_field(name="**원래 금액**", value=f"```{user_data[1]}```", inline=False)
        dm_embed.add_field(name="**충전 후 금액**", value=f"```{new_money}```", inline=False)
        dm_embed.set_footer(text="충전신청이 정상적으로 완료되었습니다\n금액 반영 안될 시 관리자한테 문의바랍니다")
        try: await target.send(embed=dm_embed)
        except: pass
        await interaction.response.edit_message(content=f"✅ {target.name} 충전 승인 완료", embed=None, view=None)

    @ui.button(label="거부", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: ui.Button):
        target = await bot.fetch_user(self.target_user_id)
        dm_embed = discord.Embed(description="-# 충전신청이 관리진에 의해 거부되었습니다\n-# 문제 있을 시 관리자한테 문의바랍니다", color=discord.Color.red())
        try: await target.send(embed=dm_embed)
        except: pass
        await interaction.response.edit_message(content=f"❌ {target.name} 충전 거부 완료", embed=None, view=None)

class MainVendingView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="충전", style=discord.ButtonStyle.secondary, emoji="<:1302328427545624689:1453761426375053322>")
    async def charge(self, interaction: discord.Interaction, button: ui.Button):
        cur.execute("SELECT method FROM payment_settings WHERE allowed = 1")
        allowed = [r[0] for r in cur.fetchall()]
        if not allowed: return await interaction.response.send_message("사용 가능한 결제 수단이 없습니다.", ephemeral=True)
        
        embed = discord.Embed(title="💳 결제 수단 선택", description="결제하실 수단을 선택해주세요.", color=discord.Color.greyple())
        view = ui.View()
        for method in allowed:
            btn = ui.Button(label=method, style=discord.ButtonStyle.primary)
            if method == "계좌이체": btn.callback = lambda i: i.response.send_modal(ChargeModal())
            view.add_item(btn)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="구매", style=discord.ButtonStyle.secondary, emoji="<:1302328347765899395:1453761428614811709>")
    async def buy(self, interaction: discord.Interaction, button: ui.Button):
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall()
        if not cats: return await interaction.response.send_message("등록된 제품이 없습니다.", ephemeral=True)
        
        view = ui.View()
        select = ui.Select(placeholder="카테고리 선택")
        for cat in cats: select.add_option(label=cat[0], value=cat[0])
        
        async def cat_callback(i: discord.Interaction):
            cat_name = select.values[0]
            cur.execute("SELECT name, price, emoji FROM products WHERE category = ?", (cat_name,))
            prods = cur.fetchall()
            p_view = ui.View()
            p_sel = ui.Select(placeholder="제품 선택")
            for p in prods: p_sel.add_option(label=f"{p[0]} ({p[1]}원)", value=p[0], emoji=p[2] if p[2] else None)
            
            async def p_callback(pi: discord.Interaction):
                p_name = p_sel.values[0]
                modal = ui.Modal(title="수량 입력")
                amount_in = ui.TextInput(label="구매 수량", placeholder="1")
                modal.add_item(amount_in)
                
                async def amount_submit(mi: discord.Interaction):
                    amount = int(amount_in.value)
                    cur.execute("SELECT price, stock FROM products WHERE name = ?", (p_name,))
                    price, stock_str = cur.fetchone()
                    stocks = stock_str.split('\n') if stock_str else []
                    if len(stocks) < amount: return await mi.response.send_message("재고가 부족합니다.", ephemeral=True)
                    
                    total_price = price * amount
                    user_data = get_user(mi.user.id)
                    if user_data[1] < total_price: return await mi.response.send_message("잔액이 부족합니다.", ephemeral=True)
                    
                    new_money = user_data[1] - total_price
                    bought_items = stocks[:amount]
                    cur.execute("UPDATE users SET money = ? WHERE id = ?", (new_money, mi.user.id))
                    cur.execute("UPDATE products SET stock = ? WHERE name = ?", ('\n'.join(stocks[amount:]), p_name))
                    db.commit()

                    await mi.response.edit_message(content="-# 성공적으로 구매 완료되었습니다\n-# 봇 DM에 제품이 정상적으로 전송되었습니다", embed=None, view=None)
                    
                    dm_embed = discord.Embed(color=discord.Color.blue())
                    dm_embed.description = f"**구매한 제품**\n```{p_name}```\n**제품 수량**\n```{amount}```\n**차감된 금액**\n```{total_price}```\n" \
                                           f"ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ\n\n**제품 보기**\n\n" + "\n".join(bought_items)
                    
                    review_view = ui.View()
                    log_ch_id = get_log_channel("후기로그")
                    r_btn = ui.Button(label="후기 작성", style=discord.ButtonStyle.success)
                    r_btn.callback = lambda ri: ri.response.send_modal(ReviewModal(p_name, amount, total_price, log_ch_id))
                    review_view.add_item(r_btn)
                    try: await mi.user.send(embed=dm_embed, view=review_view)
                    except: pass

                modal.on_submit = amount_submit
                await pi.response.send_modal(modal)
            
            p_sel.callback = p_callback
            p_view.add_item(p_sel)
            await i.response.edit_message(content="제품을 선택해주세요.", view=p_view)

        select.callback = cat_callback
        view.add_item(select)
        await interaction.response.send_message("카테고리를 선택해주세요.", view=view, ephemeral=True)

    @ui.button(label="내 정보", style=discord.ButtonStyle.secondary, emoji="<:1306285145132892180:1453761427344199872>")
    async def my_info(self, interaction: discord.Interaction, button: ui.Button):
        data = get_user(interaction.user.id)
        embed = discord.Embed(title=f"👤 {interaction.user.name}님의 정보", color=discord.Color.blue())
        embed.description = f"**남은 잔액**\n``` {data[1]} ```\n**누적 금액**\n``` {data[2]} ```\n**등급 할인**\n``` {data[3]} | 테스트 ```"
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 명령어 정의 ---

@bot.tree.command(name="버튼자판기", description="자판기를 생성합니다.")
async def vending(interaction: discord.Interaction):
    await interaction.response.send_message("버튼 자판기 생성 완료되었습니다.", ephemeral=True)
    embed = discord.Embed(title="🏪 자판기 메인", description="원하시는 메뉴를 선택해주세요.", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=MainVendingView())

@bot.tree.command(name="결제수단설정")
async def set_pay(interaction: discord.Interaction, 계좌이체: str, 문화상품권: str, 코인결제: str):
    m = {"허용": 1, "거부": 0}
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('계좌이체', ?)", (m.get(계좌이체, 0),))
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('문화상품권', ?)", (m.get(문화상품권, 0),))
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('코인결제', ?)", (m.get(코인결제, 0),))
    db.commit()
    await interaction.response.send_message("설정 완료.", ephemeral=True)

@bot.tree.command(name="결제수단관리")
async def manage_pay(interaction: discord.Interaction):
    view = ui.View()
    select = ui.Select(placeholder="수단 선택")
    select.add_option(label="계좌이체", value="bank")
    async def callback(i: discord.Interaction):
        if select.values[0] == "bank":
            modal = ui.Modal(title="계좌 정보 설정")
            owner = ui.TextInput(label="예금주"); bank = ui.TextInput(label="은행명"); num = ui.TextInput(label="계좌번호")
            modal.add_item(owner); modal.add_item(bank); modal.add_item(num)
            async def s(mi: discord.Interaction):
                cur.execute("INSERT OR REPLACE INTO settings VALUES ('bank_info', ?)", (f"{owner.value}|{bank.value}|{num.value}",))
                db.commit(); await mi.response.send_message("저장 완료.", ephemeral=True)
            modal.on_submit = s
            await i.response.send_modal(modal)
    select.callback = callback
    view.add_item(select)
    await interaction.response.send_message("관리할 수단을 선택하세요.", view=view, ephemeral=True)

@bot.tree.command(name="로그설정")
async def set_log(interaction: discord.Interaction):
    view = ui.View()
    select = ui.Select(placeholder="로그 종류 선택")
    for t in ["관리자로그", "충전로그", "구매로그", "후기로그"]: select.add_option(label=t, value=t)
    async def callback(i: discord.Interaction):
        log_type = select.values[0]
        modal = ui.Modal(title=f"{log_type} 설정")
        chid = ui.TextInput(label="채널 ID")
        modal.add_item(chid)
        async def s(mi: discord.Interaction):
            cur.execute("INSERT OR REPLACE INTO logs VALUES (?, ?)", (log_type, int(chid.value)))
            db.commit(); await mi.response.send_message("설정 완료.", ephemeral=True)
        modal.on_submit = s
        await i.response.send_modal(modal)
    select.callback = callback
    view.add_item(select)
    await interaction.response.send_message("로그 채널을 선택하세요.", view=view, ephemeral=True)

@bot.tree.command(name="제품설정")
async def prod_set(interaction: discord.Interaction):
    view = ui.View()
    select = ui.Select(placeholder="작업 선택")
    select.add_option(label="제품추가", value="add"); select.add_option(label="제품삭제", value="del"); select.add_option(label="제품설정", value="edit")
    async def callback(i: discord.Interaction):
        work = select.values[0]
        if work == "add":
            modal = ui.Modal(title="제품 추가")
            name = ui.TextInput(label="제품이름"); cat = ui.TextInput(label="카테고리")
            modal.add_item(name); modal.add_item(cat)
            async def s(mi: discord.Interaction):
                cur.execute("INSERT INTO products (name, category, price) VALUES (?, ?, 0)", (name.value, cat.value))
                db.commit(); await mi.response.send_message("추가 완료.", ephemeral=True)
            modal.on_submit = s
            await i.response.send_modal(modal)
        elif work == "del":
            cur.execute("SELECT name FROM products"); prods = cur.fetchall()
            d_view = ui.View(); d_sel = ui.Select(placeholder="삭제할 제품 선택")
            for p in prods: d_sel.add_option(label=p[0], value=p[0])
            async def d_callback(di: discord.Interaction):
                cur.execute("DELETE FROM products WHERE name = ?", (d_sel.values[0],))
                db.commit(); await di.response.send_message("삭제 완료.", ephemeral=True)
            d_sel.callback = d_callback; d_view.add_item(d_sel)
            await i.response.send_message("제품을 선택하세요.", view=d_view, ephemeral=True)
        elif work == "edit":
            cur.execute("SELECT name FROM products"); prods = cur.fetchall()
            e_view = ui.View(); e_sel = ui.Select(placeholder="설정할 제품 선택")
            for p in prods: e_sel.add_option(label=p[0], value=p[0])
            async def e_callback(ei: discord.Interaction):
                p_name = e_sel.values[0]
                modal = ui.Modal(title="제품 상세 설정")
                cat = ui.TextInput(label="카테고리"); p_e = ui.TextInput(label="제품 이모지"); c_e = ui.TextInput(label="카테고리 이모지")
                pr = ui.TextInput(label="가격"); st = ui.TextInput(label="재고", style=discord.TextStyle.paragraph)
                for item in [cat, p_e, c_e, pr, st]: modal.add_item(item)
                async def es(mi: discord.Interaction):
                    cur.execute("UPDATE products SET category=?, emoji=?, cat_emoji=?, price=?, stock=? WHERE name=?", (cat.value, p_e.value, c_e.value, int(pr.value), st.value, p_name))
                    db.commit(); await mi.response.send_message("수정 완료.", ephemeral=True)
                modal.on_submit = es
                await ei.response.send_modal(modal)
            e_sel.callback = e_callback; e_view.add_item(e_sel)
            await i.response.send_message("제품을 선택하세요.", view=e_view, ephemeral=True)
    select.callback = callback
    view.add_item(select)
    await interaction.response.send_message("작업을 선택하세요.", view=view, ephemeral=True)

bot.run("YOUR_BOT_TOKEN_HERE")
