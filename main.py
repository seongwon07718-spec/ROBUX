if __name__ == "__main__":
    import requests
    api = RobloxAPI()
    
    # 응답 raw 확인
    url = "https://games.roblox.com/v1/games/189707/game-passes?limit=100&sortOrder=Asc"
    resp = api.session.get(url)
    print(f"status: {resp.status_code}")
    print(f"body: {resp.text}")
