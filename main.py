# --- [수정 부분 1: get_user_places 함수 교체] ---
    def get_user_places(self, user_id):
        # [변경] 기존 v2/users API는 누락이 많아 v1/users/experiences API로 교체
        # 이 API가 유저의 프로필에 등록된 모든 '실제 게임'을 가장 정확하게 가져옵니다.
        url = f"https://games.roblox.com/v1/users/{user_id}/games?accessFilter=Public&limit=50"
        resp = self.session.get(url)
        if resp.status_code != 200: return []
        return resp.json().get("data", [])

# --- [수정 부분 2: PlaceSelectView 내 드롭다운 로직 보강] ---
class PlaceSelectView(ui.LayoutView):
    def __init__(self, places, user_id):
        super().__init__(timeout=60)
        self.places, self.user_id = places, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### 🎮 마켓플레이스 선택\n게임패스가 포함된 게임을 골라주세요."))
        
        select = ui.Select(placeholder="게임을 선택하세요...")
        
        # 중복 제거 및 유효한 유니버스 ID만 필터링
        seen_universes = set()
        for p in self.places:
            u_id = p.get('id')
            if u_id and u_id not in seen_universes:
                p_name = p.get('name', '이름 없는 게임')
                # 드롭다운 옵션 추가 (최대 25개)
                if len(seen_universes) < 25:
                    select.add_option(label=p_name[:100], value=str(u_id))
                    seen_universes.add(u_id)
        
        if not seen_universes:
            con.add_item(ui.TextDisplay("⚠️ 선택 가능한 공개 게임이 없습니다."))
        else:
            select.callback = self.on_select
            con.add_item(ui.ActionRow().add_item(select))
            
        self.clear_items(); self.add_item(con)
        return self

