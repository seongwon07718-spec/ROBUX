# --- [ 모달 정의: DB 저장 로직 포함 ] ---
class ProductModal(ui.Modal, title="제품 등록/수정"):
    cat = ui.TextInput(label="카테고리", placeholder="예: 음료, 과자")
    name = ui.TextInput(label="제품명", placeholder="예: 코카콜라")
    price = ui.TextInput(label="가격", placeholder="숫자만 입력 (예: 1500)")

    async def on_submit(self, it: discord.Interaction):
        if not self.price.value.isdigit():
            return await it.response.send_message("❌ 가격은 숫자만 입력해주세요.", ephemeral=True)
        
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        # INSERT OR REPLACE로 기존 제품이 있으면 업데이트, 없으면 추가
        cur.execute("INSERT OR REPLACE INTO products (category, name, price, stock) VALUES (?, ?, ?, COALESCE((SELECT stock FROM products WHERE name = ?), 0))", 
                    (self.cat.value, self.name.value, int(self.price.value), self.name.value))
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ **{self.name.value}** 제품이 DB에 반영되었습니다.", ephemeral=True)

class StockModal(ui.Modal, title="재고 수량 관리"):
    name = ui.TextInput(label="제품명", placeholder="수정할 제품의 정확한 이름을 입력하세요")
    count = ui.TextInput(label="변경할 재고 수량", placeholder="숫자 입력 (예: 50)")

    async def on_submit(self, it: discord.Interaction):
        if not self.count.value.isdigit():
            return await it.response.send_message("❌ 수량은 숫자만 입력해주세요.", ephemeral=True)

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock = ? WHERE name = ?", (int(self.count.value), self.name.value))
        if cur.rowcount == 0:
            conn.close()
            return await it.response.send_message("❌ 해당 이름의 제품을 찾을 수 없습니다.", ephemeral=True)
        conn.commit(); conn.close()
        await it.response.send_message(f"✅ **{self.name.value}**의 재고가 {self.count.value}개로 수정되었습니다.", ephemeral=True)

# --- [ 관리자 전용 레이아웃 ] ---
class ProductAdminLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.container = ui.Container(ui.TextDisplay("## ⚙️ 상품 관리 도구"), accent_color=0x2b2d31)
        self.select = ui.Select(placeholder="설정할 항목을 선택하세요", options=[
            discord.SelectOption(label="제품 등록/수정", value="prod", emoji="📦", description="이름 및 가격 설정"),
            discord.SelectOption(label="재고 수량 설정", value="stock", emoji="📊", description="남은 갯수 수정")
        ])
        self.select.callback = self.admin_callback
        self.container.add_item(ui.ActionRow(self.select))
        self.add_item(self.container)

    async def admin_callback(self, it: discord.Interaction):
        if self.select.values[0] == "prod": await it.response.send_modal(ProductModal())
        else: await it.response.send_modal(StockModal())

@bot.tree.command(name="상품설정", description="자판기 상품 정보를 관리합니다 (관리자)")
async def product_setting(it: discord.Interaction):
    if not it.user.guild_permissions.administrator:
        return await it.response.send_message("권한이 없습니다.", ephemeral=True)
    await it.response.send_message(view=ProductAdminLayout(), ephemeral=True)
