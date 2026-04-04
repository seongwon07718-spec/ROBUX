class RobloxAPI:
    def __init__(self, cookie=None):
        self.session = requests.Session()
        if cookie:
            clean_cookie = cookie.split('=')[-1] if '=' in cookie else cookie
            self.session.cookies.set(".ROBLOSECURITY", clean_cookie)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

    def get_csrf_token(self):
        resp = self.session.post("https://auth.roblox.com/v2/logout", headers=self.headers)
        return resp.headers.get("x-csrf-token")

    def get_user_id(self, nickname):
        url = "https://users.roblox.com/v1/usernames/users"
        resp = self.session.post(url, json={"usernames": [nickname], "excludeBannedUsers": True})
        data = resp.json().get("data", [])
        return data[0].get("id") if data else None

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

    def get_place_gamepasses(self, universe_id):
        """
        [수정] 게임패스를 찾지 못하는 문제를 해결하기 위해 
        가장 정확한 v1 게임패스 목록 API를 사용합니다.
        """
        url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes?limit=50"
        resp = self.session.get(url)
        if resp.status_code != 200: return []
        
        data = resp.json().get("data", [])
        # 가격이 설정되지 않은(판매 중지) 패스는 필터링
        return [p for p in data if p.get('price') is not None]

# -----------------------------------
# 2️⃣ 결제 처리 로직
# -----------------------------------
def process_manual_buy(pass_id, user_id, money):
    conn = sqlite3.connect(DATABASE); cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key = 'roblox_cookie'")
    row = cur.fetchone(); conn.close()
    if not row: return {"success": False, "message": "쿠키가 없습니다."}

    api = RobloxAPI(row[0])
    info_resp = api.session.get(f"https://economy.roblox.com/v1/game-pass/{pass_id}/product-info")
    if info_resp.status_code != 200: return {"success": False, "message": "상품 조회 실패"}
    info = info_resp.json()
    
    token = api.get_csrf_token()
    headers = api.headers.copy()
    headers.update({
        "x-csrf-token": token, 
        "Content-Type": "application/json", 
        "Referer": f"https://www.roblox.com/game-pass/{pass_id}"
    })
    
    payload = {
        "expectedCurrency": 1, 
        "expectedPrice": info.get("PriceInRobux", 0), 
        "expectedSellerId": info.get("Creator", {}).get("Id")
    }
    buy_url = f"https://economy.roblox.com/v1/purchases/products/{info.get('ProductId')}"
    
    resp = api.session.post(buy_url, json=payload, headers=headers)
    result = resp.json()
    
    if resp.status_code == 200 and result.get("purchased"):
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (money, user_id))
        cur.execute("INSERT INTO orders (order_id, user_id, amount, robux, status) VALUES (?, ?, ?, ?, 'SUCCESS')",
                    (order_id, user_id, money, info.get("PriceInRobux", 0)))
        conn.commit(); conn.close()
        return {"success": True, "order_id": order_id}
    
    return {"success": False, "message": result.get("reason", "구매 조건이 맞지 않습니다.")}

# -----------------------------------
# 3️⃣ UI 클래스 (KeyError 수정됨)
# -----------------------------------

class FinalBuyView(ui.LayoutView):
    def __init__(self, pass_info, money, user_id):
        super().__init__(timeout=60)
        self.pass_info, self.money, self.user_id = pass_info, money, str(user_id)

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        text = f"### <:acy2:1489883409001091142> 최종 결제 확인\n-# - **아이템**: {self.pass_info.get('name')}\n-# - **로벅스**: {self.pass_info.get('price'):,} R$\n-# - **차감금액**: {self.money:,}원"
        con.add_item(ui.TextDisplay(text))
        row = ui.ActionRow()
        btn = ui.Button(label="결제 승인", style=discord.ButtonStyle.gray, emoji="✅")
        btn.callback = self.do_buy
        row.add_item(btn)
        con.add_item(row)
        self.clear_items(); self.add_item(con)
        return self

    async def do_buy(self, it: discord.Interaction):
        await it.response.edit_message(view=get_container_view("⌛ 처리 중", "서버 통신 중...", 0xFEE75C))
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, process_manual_buy, self.pass_info['id'], self.user_id, self.money)
        if res["success"]:
            await it.edit_original_response(view=get_container_view("✅ 성공", f"주문번호: `{res['order_id']}`", 0x57F287))
        else:
            await it.edit_original_response(view=get_container_view("❌ 실패", res["message"], 0xED4245))

class PassSelectView(ui.LayoutView):
    def __init__(self, passes, user_id):
        super().__init__(timeout=60)
        self.passes, self.user_id = passes, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  게임패스 선택\n-# - 구매할 게임패스를 선택하세요"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        select = ui.Select(placeholder="게임패스를 선택해주세요")
        for p in self.passes[:25]:
            p_id = p.get('id')
            p_name = p.get('name', '이름 없음')
            p_price = p.get('price', 0)
            if p_id:
                select.add_option(label=f"{p_name} ({p_price} R$)", value=str(p_id))
        
        select.callback = self.on_select
        con.add_item(ui.ActionRow().add_item(select))
        self.clear_items(); self.add_item(con)
        return self

    async def on_select(self, it: discord.Interaction):
        selected_id = int(it.data['values'][0])
        pass_data = next(p for p in self.passes if p['id'] == selected_id)
        
        conn = sqlite3.connect(DATABASE); cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'robux_rate'")
        r = cur.fetchone(); conn.close()
        rate = int(r[0]) if r else 1000
        money = int((pass_data.get('price', 0) / rate) * 10000)

        view = FinalBuyView(pass_data, money, it.user.id)
        await it.response.edit_message(view=await view.build())

class PlaceSelectView(ui.LayoutView):
    def __init__(self, places, user_id):
        super().__init__(timeout=60)
        self.places, self.user_id = places, user_id

    async def build(self):
        con = ui.Container()
        con.accent_color = 0x5865F2
        con.add_item(ui.TextDisplay("### <:acy2:1489883409001091142>  게임 선택\n-# - 게임패스를 구매할 게임을 선택해주세요"))
        con.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        select = ui.Select(placeholder="게임을 선택해주세요")
        seen_universes = set()
        for p in self.places:
            u_id = p.get('id')
            if u_id and u_id not in seen_universes:
                p_name = p.get('name', '이름 없는 게임')
                if len(seen_universes) < 25:
                    select.add_option(label=p_name[:100], value=str(u_id))
                    seen_universes.add(u_id)
        
        if not seen_universes:
            con.add_item(ui.TextDisplay("⚠️ 선택 가능한 공개 게임이 없습니다"))
        else:
            select.callback = self.on_select
            con.add_item(ui.ActionRow().add_item(select))
            
        self.clear_items(); self.add_item(con)
        return self

class NicknameSearchModal(ui.Modal, title="유저 검색"):
    nick_input = ui.TextInput(label="로블록스 닉네임", placeholder="로블록스 닉네임을 정확하게 입력해주세요", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        api = RobloxAPI()
        user_id = api.get_user_id(self.nick_input.value.strip())
        
        if not user_id:
            return await it.followup.send(view=get_container_view("❌ 실패", "-# - 유저를 찾을 수 없습니다", 0xED4245), ephemeral=True)
        
        places = api.get_user_places(user_id)
        if not places:
            return await it.followup.send(view=get_container_view("❌ 결과 없음", "-# - 공개된 게임이 없습니다", 0xED4245), ephemeral=True)
            
        view = PlaceSelectView(places, it.user.id)
        await it.followup.send(view=await view.build(), ephemeral=True)
