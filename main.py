def get_user_id(self, nickname: str) -> int | None:
    resp = self.session.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": [nickname], "excludeBannedUsers": False},
    )
    print(f"[유저검색] status={resp.status_code} body={resp.text}")  # 디버그
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", [])
    return data[0].get("id") if data else None

def get_user_places(self, user_id: int) -> list[dict]:
    url = f"https://games.roblox.com/v2/users/{user_id}/games?limit=50&sortOrder=Asc"
    resp = self.session.get(url)
    print(f"[게임목록] status={resp.status_code} body={resp.text}")  # 디버그
    # ... 나머지 동일
