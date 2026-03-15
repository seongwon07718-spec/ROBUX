import sqlite3
import discord
from discord import ui

# --- [ 1단계: 재고 수정 프로세스 통합 뷰 ] ---
class StockEditView(ui.LayoutView):
    def __init__(self, category=None):
        super().__init__(timeout=60)
        self.category = category
        
        # 디자인 설정 (메시지 수정 시 사용될 컨테이너)
        if not self.category:
            # [기본 화면] 카테고리 선택
            self.con = ui.Container(ui.TextDisplay("## 📝 재고 수정 - 카테고리 선택"), accent_color=0x000000)
            self.con.add_item(ui.TextDisplay("수정할 제품이 속한 **카테고리**를 선택하세요."))
            self.add_category_select()
        else:
            # [전환 화면] 제품 선택
            self.con = ui.Container(ui.TextDisplay(f"## 📦 [{self.category}] 제품 선택"), accent_color=0x000000)
            self.con.add_item(ui.TextDisplay("재고 데이터를 직접 수정할 **제품**을 선택하세요."))
            self.add_product_select()

        self.add_item(self.con)

    def add_category_select(self):
        """카테고리 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM products")
        cats = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=c[0], value=c[0]) for c in cats] if cats else [discord.SelectOption(label="카테고리 없음", value="none")]
        select = ui.Select(placeholder="카테고리 선택...", options=options)
        select.callback = self.category_callback
        self.con.add_item(ui.ActionRow(select))

    def add_product_select(self):
        """제품 드롭다운 추가"""
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM products WHERE category = ?", (self.category,))
        prods = cur.fetchall(); conn.close()
        
        options = [discord.SelectOption(label=p[0], value=p[0]) for p in prods] if prods else [discord.SelectOption(label="제품 없음", value="none")]
        select = ui.Select(placeholder="제품 선택...", options=options)
        select.callback = self.product_callback
        self.con.add_item(ui.ActionRow(select))

    async def category_callback(self, it: discord.Interaction):
        selected = it.data['values'][0]
        if selected == "none": return
        
        # [핵심] 새로운 메시지를 보내지 않고, 현재 메시지를 수정해서 '제품 선택' 화면으로 바꿉니다.
        new_view = StockEditView(category=selected)
        await it.response.edit_message(view=new_view)

    async def product_callback(self, it: discord.Interaction):
        prod_name = it.data['values'][0]
        if prod_name == "none": return
        
        # DB에서 현재 재고 데이터(텍스트 전체) 가져오기
        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("SELECT stock_data FROM products WHERE name = ?", (prod_name,))
        res = cur.fetchone(); conn.close()
        current_data = res[0] if res and res[0] else ""
        
        # 최종 단계: 재고 리스트 수정 모달 띄우기
        await it.response.send_modal(StockDataListModal(prod_name, current_data))

# --- [ 2단계: 재고 데이터 직접 수정 모달 ] ---
class StockDataListModal(ui.Modal):
    def __init__(self, name, current_data):
        super().__init__(title=f"📝 {name} 재고 관리")
        self.name = name
        
        # 기존 재고 데이터를 텍스트 상자에 담아서 보여줌
        self.data_input = ui.TextInput(
            label="재고 리스트 (한 줄에 하나씩)",
            style=discord.TextStyle.paragraph,
            default=current_data, # 기존 데이터 로드
            placeholder="수정하거나 삭제할 줄을 직접 편집하세요.",
            required=False
        )
        self.add_item(self.data_input)

    async def on_submit(self, it: discord.Interaction):
        updated_data = self.data_input.value
        # 줄 바꿈 기준으로 남은 재고 개수 계산
        new_count = len([l for l in updated_data.split('\n') if l.strip()])

        conn = sqlite3.connect('vending_data.db'); cur = conn.cursor()
        cur.execute("UPDATE products SET stock_data = ?, stock = ? WHERE name = ?", 
                    (updated_data, new_count, self.name))
        conn.commit(); conn.close()
        
        await it.response.send_message(f"✅ **{self.name}** 재고 수정 완료! (현재: {new_count}개)", ephemeral=True)
