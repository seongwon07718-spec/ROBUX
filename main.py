if __name__ == "__main__":
    api = RobloxAPI()
    
    # 여러 엔드포인트 직접 테스트
    test_universe = 29407759
    
    urls = [
        f"https://games.roblox.com/v1/games/{test_universe}/game-passes?limit=100",
        f"https://www.roblox.com/games/get-game-passes?gameId={test_universe}&page=1&pageSize=100",
        f"https://catalog.roblox.com/v1/search/items?Category=34&creatorTargetId={test_universe}&limit=30",
    ]
    
    for url in urls:
        resp = api.session.get(url)
        print(f"\nURL: {url}")
        print(f"status: {resp.status_code}")
        print(f"body: {resp.text[:300]}")
