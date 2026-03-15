import sqlite3
import discord
from discord import ui

# --- [ 1. 공용 드롭다운 컴포넌트 ] ---
class CategorySelect(ui.Select):
    def __init__(self):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        # 데이터가 없을 경우를 대비한 예외 처리
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        super().__init__(placeholder="카테고리를 선택하세요", options=options, min_values=1, max_values=1)

class ProductSelect(ui.Select):
    def __init__(self, category):
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (category,))
        prods = cur.fetchall(); conn.close()
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        super().__init__(placeholder="제품을 선택하세요", options=options, min_values=1, max_values=1)

# --- [ 2. 제품 설정 및 입고 모달 (최종 단계) ] ---
class ProductEditModal(ui.Modal):
    def __init__(self, category):
        super().__init__(title=f"⚙️ [{category}] 제품 설정")
        self.category = category

        # UI 요소 순차적 추가 (노란 줄 에러 해결)
        self.prod_dropdown = ui.Label(
            text=f"수정할 {category} 제품을 선택하세요",
            component=ProductSelect(category=category)
        )
        self.add_item(self.prod_dropdown)

        self.price_input = ui.TextInput(label="가격 (숫자만)", placeholder="가격을 수정하려면 입력", required=False)
        self.add_item(self.price_input)

        self.stock_input = ui.TextInput(
            label="재고 입고 (줄바꿈당 1개)", 
            style=discord.TextStyle.paragraph, 
            placeholder="내용을 입력하세요. 입력한 줄 수만큼 재고가 자동으로 합산됩니다.",
            required=False
        )
        self.add_item(self.stock_input)

    async def on_submit(self, it: discord.Interaction):
        name = self.prod_dropdown.component.values[0]
        if name == "none":
            return await it.response.send_message("❌ 관리할 제품이 없습니다.", ephemeral=True)

        # 줄바꿈 기준 재고 계산 로직
        lines = self.stock_input.value.split('\n')
        add_count = len([l for l in lines if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # 가격 업데이트
        if self.price_input.value and self.price_input.value.isdigit():
            cur.execute("UPDATE products SET price = ? WHERE name = ?", (int(self.price_input.value), name))
        
        # 재고 입고 (기존 재고 + 줄 수)
        if add_count > 0:
            cur.execute("UPDATE products SET stock = stock + ? WHERE name = ?", (add_count, name))
        
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ **{name}** 설정 및 **{add_count}개** 입고가 완료되었습니다!", ephemeral=True)

# --- [ 3. 카테고리 선택 컨테이너 (채팅창 전송용) ] ---
class CategorySelectView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=60)
        # 400 Bad Request 방지를 위해 Container 내부 텍스트 사용
        self.container = ui.Container(ui.TextDisplay("## 📁 카테고리 선택"), accent_color=0x000000)
        self.container.add_item(ui.TextDisplay("관리할 제품이 포함된 **카테고리**를 선택해 주세요."))
        
        self.cat_select = CategorySelect()
        self.cat_select.callback = self.category_callback
        
        self.container.add_item(ui.ActionRow(self.cat_select))
        self.add_item(self.container)

    async def category_callback(self, it: discord.Interaction):
        selected_cat = self.cat_select.values[0]
        if selected_cat == "none":
            return await it.response.send_message("❌ 선택 가능한 카테고리가 없습니다.", ephemeral=True)
        
        # 카테고리 선택 시 즉시 모달 출력
        await it.response.send_modal(ProductEditModal(selected_cat))

# --- [ 4. 신규 상품 등록 모달 ] ---
class NewProductModal(ui.Modal, title="✨ 신규 상품 등록"):
    cat = ui.TextInput(label="카테고리", placeholder="예: 음식")
    name = ui.TextInput(label="제품명", placeholder="등록할 제품 이름")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("❌ 가격은 숫자만 입력해 주세요.", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                    (self.cat.value, self.name.value, int(self.price.value), 0))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ **{self.name.value}** 등록 완료!", ephemeral=True)

# --- [ 5. 메인 관리자 레이아웃 ] ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## 🛠️ 자판기 관리 메뉴"), accent_color=0x000000)
        
        btn_new = ui.Button(label="신규상품", style=discord.ButtonStyle.success, emoji="✨")
        btn_edit = ui.Button(label="상품설정", style=discord.ButtonStyle.primary, emoji="⚙️")
        
        btn_new.callback = self.new_callback
        btn_edit.callback = self.edit_callback
        
        self.container.add_item(ui.ActionRow(btn_new, btn_edit))
        self.add_item(self.container)

    async def new_callback(self, it: discord.Interaction):
        await it.response.send_modal(NewProductModal())

    async def edit_callback(self, it: discord.Interaction):
        # 모달 대신 카테고리 선택 컨테이너 전송
        await it.response.send_message(view=CategorySelectView(), ephemeral=True)

# --- [ 6. 명령어 등록 ] ---
@bot.tree.command(name="상품설정", description="상품 관리 도구를 출력합니다.")
async def admin_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
    
    # 400 에러 방지: content 필드를 비우고 전송
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)
