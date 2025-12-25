import discord
from discord import app_commands, ui
from discord.ext import commands
import sqlite3
import datetime

# --- 데이터베이스 초기화 ---
db = sqlite3.connect("vending_machine.db")
cur = db.cursor()

# 테이블 생성
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

# --- 모달 및 뷰 클래스 정의 ---

# 1. 후기 작성 모달
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
        embed = discord.Embed(title="✨ 새로운 후기 도착", color=discord.Color.gold())
        embed.add_field(name="제품", value=f"```{self.product_name}```", inline=False)
        embed.add_field(name="수량", value=f"```{self.amount}```", inline=True)
        embed.add_field(name="금액", value=f"```{self.price}```", inline=True)
        embed.add_field(name="유저", value=f"**{interaction.user.name}**", inline=False)
        embed.add_field(name="별점", value=f"**{stars} ({self.rating.value}점)**", inline=False)
        embed.add_field(name="후기", value=f"**{self.content.value}**", inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.send_message("후기가 성공적으로 등록되었습니다!", ephemeral=True)

# 2. 계좌 정보 설정 모달
class AccountSettingModal(ui.Modal, title="계좌 정보 설정"):
    owner = ui.TextInput(label="예금주", placeholder="홍길동")
    bank = ui.TextInput(label="은행명", placeholder="신한은행")
    num = ui.TextInput(label="계좌번호", placeholder="110-123-456789")

    async def on_submit(self, interaction: discord.Interaction):
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('bank_info', ?)", 
                    (f"{self.owner.value}|{self.bank.value}|{self.num.value}",))
        db.commit()
        await interaction.response.send_message("계좌 정보가 저장되었습니다.", ephemeral=True)

# 3. 충전 신청 모달
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
        
        # 유저에게 계좌 정보 안내
        embed = discord.Embed(title="계좌 입금 안내", color=discord.Color.blue())
        embed.add_field(name="예금주", value=f"```{owner}```", inline=False)
        embed.add_field(name="은행명", value=f"```{bank}```", inline=False)
        embed.add_field(name="계좌번호", value=f"```{num}```", inline=False)
        embed.set_footer(text="5분안에 입금해주셔야 자동충전됩니다\n자동충전 안될 시 관리자한테 문의바랍니다")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # 관리자 로그 전송
        log_ch = bot.get_channel(log_ch_id)
        log_embed = discord.Embed(title="충전 신청 발생", color=discord.Color.orange())
        log_embed.add_field(name="신청 유저", value=f"```{interaction.user.name} | {interaction.user.id}```", inline=False)
        log_embed.add_field(name="신청 금액", value=f"```{self.amount.value}```", inline=True)
        log_embed.add_field(name="입금자명", value=f"```{self.name.value}```", inline=True)
        
        view = ChargeAdminView(interaction.user.id, int(self.amount.value))
        await log_ch.send(embed=log_embed, view=view)

# --- 관리용 뷰 클래스 ---
class ChargeAdminView(ui.View):
    def __init__(self, user_id, amount):
        super().__init__(timeout=None)
        self.target_user_id = user_id
        self.amount = amount

    @ui.button(label="허용", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction):
        user_data = get_user(self.target_user_id)
        new_money = user_data[1] + self.amount
        cur.execute("UPDATE users SET money = ?, total_pay = total_pay + ? WHERE id = ?", (new_money, self.amount, self.target_user_id))
        db.commit()
        
        target = await bot.fetch_user(self.target_user_id)
        dm_embed = discord.Embed(title="충전 완료 알림", color=discord.Color.green())
        dm_embed.add_field(name="충전 금액", value=f"```{self.amount}```", inline=False)
        dm_embed.add_field(name="원래 금액", value=f"```{user_data[1]}```", inline=False)
        dm_embed.add_field(name="충전 후 금액", value=f"```{new_money}```", inline=False)
        dm_embed.set_footer(text="충전신청이 정상적으로 완료되었습니다\n금액 반영 안될 시 관리자한테 문의바랍니다")
        try: await target.send(embed=dm_embed)
        except: pass
        
        await interaction.response.edit_message(content=f"✅ {target.name}님 충전 승인 완료", embed=None, view=None)

    @ui.button(label="거부", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction):
        target = await bot.fetch_user(self.target_user_id)
        dm_embed = discord.Embed(description="-# 충전신청이 관리진에 의해 거부되었습니다\n-# 문제 있을 시 관리자한테 문의바랍니다", color=discord.Color.red())
        try: await target.send(embed=dm_embed)
        except: pass
        await interaction.response.edit_message(content=f"❌ {target.name}님 충전 거부 완료", embed=None, view=None)

# --- 메인 명령어 ---

@bot.tree.command(name="버튼자판기", description="자판기 임베드를 생성합니다.")
async def vending_machine(interaction: discord.Interaction):
    await interaction.response.send_message("버튼 자판기 생성 완료되었습니다.", ephemeral=True)
    
    embed = discord.Embed(title="🏪 자판기 메인", description="원하시는 메뉴를 선택해주세요.", color=discord.Color.blue())
    view = MainVendingView()
    await interaction.channel.send(embed=embed, view=view)

class MainVendingView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="충전", style=discord.ButtonStyle.secondary, emoji="<:1302328427545624689:1453761426375053322>")
    async def charge(self, interaction: discord.Interaction):
        embed = discord.Embed(title="💳 결제 수단 선택", description="결제하실 수단을 선택해주세요.", color=discord.Color.greyple())
        view = PaymentSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="구매", style=discord.ButtonStyle.secondary, emoji="<:1302328347765899395:1453761428614811709>")
    async def buy(self, interaction: discord.Interaction):
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall()
        if not cats: return await interaction.response.send_message("등록된 제품이 없습니다.", ephemeral=True)
        
        view = CategorySelectView(cats)
        await interaction.response.send_message("카테고리를 선택해주세요.", view=view, ephemeral=True)

    @ui.button(label="내 정보", style=discord.ButtonStyle.secondary, emoji="<:1306285145132892180:1453761427344199872>")
    async def my_info(self, interaction: discord.Interaction):
        data = get_user(interaction.user.id)
        embed = discord.Embed(title=f"👤 {interaction.user.name}님의 정보", color=discord.Color.blue())
        embed.description = f"**남은 잔액**\n``` {data[1]}원 ```\n**누적 금액**\n``` {data[2]}원 ```\n**등급 할인**\n``` {data[3]} | 테스트 ```"
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 결제수단 선택 뷰
class PaymentSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        cur.execute("SELECT method FROM payment_settings WHERE allowed = 1")
        allowed = [r[0] for r in cur.fetchall()]
        
        if "계좌이체" in allowed:
            btn = ui.Button(label="계좌이체", style=discord.ButtonStyle.primary)
            btn.callback = self.bank_callback
            self.add_item(btn)
        if "문화상품권" in allowed:
            self.add_item(ui.Button(label="문화상품권", style=discord.ButtonStyle.primary))
        if "코인결제" in allowed:
            self.add_item(ui.Button(label="코인결제", style=discord.ButtonStyle.primary))

    async def bank_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChargeModal())

# --- 설정 관련 명령어 ---

@bot.tree.command(name="결제수단설정", description="결제 수단 허용 여부를 설정합니다.")
@app_commands.describe(계좌이체="허용/거부", 문화상품권="허용/거부", 코인결제="허용/거부")
async def set_payment(interaction: discord.Interaction, 계좌이체: str, 문화상품권: str, 코인결제: str):
    mapping = {"허용": 1, "거부": 0}
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('계좌이체', ?)", (mapping.get(계좌이체, 0),))
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('문화상품권', ?)", (mapping.get(문화상품권, 0),))
    cur.execute("INSERT OR REPLACE INTO payment_settings VALUES ('코인결제', ?)", (mapping.get(코인결제, 0),))
    db.commit()
    await interaction.response.send_message("결제 수단 설정이 완료되었습니다.", ephemeral=True)

@bot.tree.command(name="결제수단관리", description="계좌 정보 등을 관리합니다.")
async def manage_payment(interaction: discord.Interaction):
    embed = discord.Embed(title="💰 결제수단 관리", description="정보를 설정할 수단을 선택하세요.")
    view = ui.View()
    select = ui.Select(placeholder="수단 선택...")
    select.add_option(label="계좌이체", value="bank")
    select.add_option(label="문화상품권", value="cult")
    select.add_option(label="코인결제", value="coin")
    
    async def select_callback(inter):
        if select.values[0] == "bank":
            await inter.response.send_modal(AccountSettingModal())
        else:
            await inter.response.send_message("준비 중인 기능입니다.", ephemeral=True)
            
    select.callback = select_callback
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="로그설정", description="각종 로그 채널을 설정합니다.")
async def set_log(interaction: discord.Interaction):
    embed = discord.Embed(title="📁 로그 채널 설정", description="설정할 로그 종류를 선택하세요.")
    view = ui.View()
    select = ui.Select(placeholder="로그 종류 선택...")
    for log_type in ["관리자로그", "충전로그", "구매로그", "후기로그"]:
        select.add_option(label=log_type, value=log_type)

    async def callback(inter):
        log_type = select.values[0]
        modal = ui.Modal(title=f"{log_type} 설정")
        chid_input = ui.TextInput(label="채널 ID", placeholder="1234567890")
        modal.add_item(chid_input)
        
        async def modal_submit(minter):
            cur.execute("INSERT OR REPLACE INTO logs VALUES (?, ?)", (log_type, int(chid_input.value)))
            db.commit()
            await minter.response.send_message(f"{log_type} 채널이 설정되었습니다.", ephemeral=True)
            
        modal.on_submit = modal_submit
        await inter.response.send_modal(modal)

    select.callback = callback
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- 상점 제품 관리 ---

@bot.tree.command(name="제품설정", description="제품 추가, 삭제, 설정을 관리합니다.")
async def product_manage(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ 제품 관리 시스템", description="수행할 작업을 선택하세요.")
    view = ui.View()
    select = ui.Select(placeholder="작업 선택...")
    select.add_option(label="제품추가", value="add")
    select.add_option(label="제품삭제", value="delete")
    select.add_option(label="제품설정", value="edit")

    async def callback(inter):
        work = select.values[0]
        if work == "add":
            modal = ui.Modal(title="제품 추가")
            name_in = ui.TextInput(label="제품이름")
            cat_in = ui.TextInput(label="카테고리")
            modal.add_item(name_in); modal.add_item(cat_in)
            async def add_submit(mi):
                cur.execute("INSERT INTO products (name, category, price, stock) VALUES (?, ?, 0, '없음')", (name_in.value, cat_in.value))
                db.commit()
                await mi.response.send_message(f"제품 {name_in.value} 추가 완료.", ephemeral=True)
            modal.on_submit = add_submit
            await inter.response.send_modal(modal)
            
        elif work == "delete":
            cur.execute("SELECT name FROM products")
            prods = cur.fetchall()
            if not prods: return await inter.response.send_message("삭제할 제품이 없습니다.", ephemeral=True)
            d_view = ui.View()
            d_sel = ui.Select(placeholder="삭제할 제품 선택...")
            for p in prods: d_sel.add_option(label=p[0], value=p[0])
            async def d_callback(di):
                cur.execute("DELETE FROM products WHERE name = ?", (d_sel.values[0],))
                db.commit()
                await di.response.send_message("삭제 완료.", ephemeral=True)
            d_sel.callback = d_callback
            d_view.add_item(d_sel)
            await inter.response.send_message("삭제할 제품을 선택하세요.", view=d_view, ephemeral=True)
            
        elif work == "edit":
            cur.execute("SELECT name FROM products")
            prods = cur.fetchall()
            e_view = ui.View()
            e_sel = ui.Select(placeholder="설정할 제품 선택...")
            for p in prods: e_sel.add_option(label=p[0], value=p[0])
            async def e_callback(ei):
                p_name = e_sel.values[0]
                modal = ui.Modal(title=f"{p_name} 정보 수정")
                cat = ui.TextInput(label="카테고리")
                p_emoji = ui.TextInput(label="제품 커스텀 이모지")
                c_emoji = ui.TextInput(label="카테고리 커스텀 이모지")
                price = ui.TextInput(label="제품가격")
                stock = ui.TextInput(label="재고(줄바꿈으로 구분)", style=discord.TextStyle.paragraph)
                for i in [cat, p_emoji, c_emoji, price, stock]: modal.add_item(i)
                async def edit_submit(mi):
                    cur.execute("UPDATE products SET category=?, emoji=?, cat_emoji=?, price=?, stock=? WHERE name=?",
                                (cat.value, p_emoji.value, c_emoji.value, int(price.value), stock.value, p_name))
                    db.commit()
                    await mi.response.send_message("수정 완료", ephemeral=True)
                modal.on_submit = edit_submit
                await ei.response.send_modal(modal)
            e_sel.callback = e_callback
            e_view.add_item(e_sel)
            await inter.response.send_message("수정할 제품을 선택하세요.", view=e_view, ephemeral=True)

    select.callback = callback
    view.add_item(select)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- 구매 프로세스 뷰 ---

class CategorySelectView(ui.View):
    def __init__(self, cats):
        super().__init__(timeout=None)
        select = ui.Select(placeholder="카테고리 선택")
        for cat in cats:
            select.add_option(label=cat[0], value=cat[0])
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        cat_name = interaction.data['values'][0]
        cur.execute("SELECT name, price, emoji FROM products WHERE category = ?", (cat_name,))
        prods = cur.fetchall()
        
        embed = discord.Embed(title=f"📁 {cat_name} 카테고리", description="제품을 선택해주세요.", color=discord.Color.green())
        view = ProductSelectView(prods)
        await interaction.response.edit_message(content=None, embed=embed, view=view)

class ProductSelectView(ui.View):
    def __init__(self, prods):
        super().__init__(timeout=None)
        select = ui.Select(placeholder="제품 선택")
        for p in prods:
            select.add_option(label=f"{p[0]} - {p[1]}원", value=p[0], emoji=p[2] if p[2] else None)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        p_name = interaction.data['values'][0]
        modal = ui.Modal(title="수량 입력")
        amount_in = ui.TextInput(label="구매 수량", placeholder="1")
        modal.add_item(amount_in)
        
        async def amount_submit(mi):
            amount = int(amount_in.value)
            cur.execute("SELECT price, stock FROM products WHERE name = ?", (p_name,))
            price, stock_str = cur.fetchone()
            stocks = stock_str.split('\n')
            
            if len(stocks) < amount:
                return await mi.response.send_message("재고가 부족합니다.", ephemeral=True)
            
            total_price = price * amount
            user_data = get_user(mi.user.id)
            if user_data[1] < total_price:
                return await mi.response.send_message("잔액이 부족합니다.", ephemeral=True)
            
            # 차감 및 구매 처리
            new_money = user_data[1] - total_price
            bought_items = stocks[:amount]
            remains = stocks[amount:]
            
            cur.execute("UPDATE users SET money = ? WHERE id = ?", (new_money, mi.user.id))
            cur.execute("UPDATE products SET stock = ? WHERE name = ?", ('\n'.join(remains), p_name))
            db.commit()

            # 결과 임베드
            success_embed = discord.Embed(description="-# 성공적으로 구매 완료되었습니다\n-# 봇 DM에 제품이 정상적으로 전송되었습니다", color=discord.Color.green())
            await mi.response.edit_message(embed=success_embed, view=None)
            
            # DM 전송
            dm_embed = discord.Embed(title="📦 제품 구매 완료", color=discord.Color.blue())
            dm_embed.add_field(name="구매한 제품", value=f"```{p_name}```", inline=False)
            dm_embed.add_field(name="제품 수량", value=f"```{amount}```", inline=True)
            dm_embed.add_field(name="차감된 금액", value=f"```{total_price}```", inline=True)
            dm_embed.add_field(name="제품 보기", value=f"```\n" + "\n".join(bought_items) + "```", inline=False)
            
            view = ui.View()
            log_ch_id = get_log_channel("후기로그")
            btn = ui.Button(label="후기 작성", style=discord.ButtonStyle.success)
            btn.callback = lambda i: i.response.send_modal(ReviewModal(p_name, amount, total_price, log_ch_id))
            view.add_item(btn)
            
            try: await mi.user.send(embed=dm_embed, view=view)
            except: pass

        modal.on_submit = amount_submit
        await interaction.response.send_modal(modal)

bot.run("YOUR_BOT_TOKEN_HERE")
