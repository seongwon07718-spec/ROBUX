    async def admin_callback(self, it: discord.Interaction):
        # 1. 선택된 값 가져오기
        val = self.admin_select.values[0]
        
        # 2. 조건문 시작 (반드시 elif를 사용하여 중복 실행 방지)
        if val == "add_cat":
            # 모달로 응답 (한 번의 interaction에 한 번만 가능)
            await it.response.send_modal(AddCategoryModal())
            
        elif val == "add_prod":
            # 메시지로 응답
            await it.response.send_message(view=AdminCategorySelectView(purpose="add"), ephemeral=True)
            
        elif val == "edit_cat":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_cat"), ephemeral=True)
            
        elif val == "edit_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="edit_prod"), ephemeral=True)
            
        elif val == "del_prod":
            await it.response.send_message(view=AdminCategorySelectView(purpose="delete_prod"), ephemeral=True)
            
        elif val == "del_cat":
            # 모달로 응답
            await it.response.send_modal(CategoryDeleteModal())
            
        elif val == "stock_edit":
            await it.response.send_message(view=StockCategorySelectView(), ephemeral=True)
