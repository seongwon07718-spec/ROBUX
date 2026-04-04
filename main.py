    def get_user_places(self, user_id):
        """
        [공식 games API 기반] 인벤토리가 아닌 실제 게임(Experiences) 목록만 긁어옵니다.
        accessFilter를 제거하여 로블록스 서버의 필터링 버그를 우회합니다.
        """
        # 필터를 빼고 limit을 50으로 늘려 모든 게임 데이터를 강제로 긁어옵니다.
        url = f"https://games.roblox.com/v2/users/{user_id}/games?limit=50"
        resp = self.session.get(url, headers=self.headers)
        
        if resp.status_code != 200:
            return []
            
        data = resp.json().get("data", [])
        if not data:
            return []

        valid_games = []
        for g in data:
            # 공개(Public) 설정된 게임만 선별합니다.
            if g.get('isPublic') == True:
                # 다음 단계(게임패스 조회)를 위해 Universe ID와 Place ID를 매핑합니다.
                valid_games.append({
                    'id': g.get('id'), # Universe ID
                    'name': g.get('name', '이름 없는 게임'),
                    'rootPlaceId': g.get('rootPlaceId') # Place ID
                })
        
        return valid_games

