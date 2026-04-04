    def get_user_places(self, user_id):
        """
        [최종 수정] v2/users/{id}/games가 실패할 때를 대비해 
        가장 원시적이고 확실한 v1/users/{id}/places API를 사용하여 
        유저의 모든 공개 플레이스를 긁어옵니다.
        """
        # 이 API는 유저의 '플레이스'를 직접 가져오므로 인식률이 가장 높습니다.
        url = f"https://games.roblox.com/v1/users/{user_id}/places?limit=50"
        resp = self.session.get(url)
        
        if resp.status_code != 200:
            return []
            
        data = resp.json().get("data", [])
        
        # 유니버스 ID(universeId)가 있는 것들만 골라냅니다. (게임패스 조회에 필수)
        # 로블록스에서 '플레이스' 데이터 안에는 'universeId' 필드가 반드시 포함되어 있습니다.
        valid_games = []
        for g in data:
            # universeId가 바로 'id' 필드로 쓰이거나 'universeId' 필드로 들어옵니다.
            u_id = g.get('universeId') or g.get('id')
            if u_id:
                # PlaceSelectView에서 쓰기 편하게 데이터 규격을 맞춰줍니다.
                valid_games.append({
                    'id': u_id,
                    'name': g.get('name', '이름 없는 게임'),
                    'rootPlaceId': g.get('id')
                })
        
        return valid_games

