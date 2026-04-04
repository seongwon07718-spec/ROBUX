# ❌ 기존 - LayoutView 객체 반환
def get_container_view(title: str, description: str, color: int):
    class SimpleView(ui.LayoutView):
        async def build(self):
            ...
    return SimpleView()  # 인스턴스만 반환, build() 안 호출됨


# ✅ 수정 - build()까지 호출한 결과를 반환하는 async 함수로 변경
async def get_container_view(title: str, description: str, color: int):
    class SimpleView(ui.LayoutView):
        pass

    view = SimpleView()
    con = ui.Container()
    con.accent_color = color
    con.add_item(ui.TextDisplay(f"### {title}\n-# {description}"))
    view.add_item(con)
    return view
