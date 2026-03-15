# ProductAdminLayout 클래스 내부의 admin_callback 수정
async def admin_callback(self, it: discord.Interaction):
    # 이제 'prod'인지 'stock'인지 구분할 필요 없이 하나의 모달로 통합 관리합니다.
    await it.response.send_modal(ProductManageModal())
