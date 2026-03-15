import urllib.parse # 코드 맨 윗줄에 추가

# ... 기존 코드 중 ...

domain = "rbxshop.cloud"
# 제품명(self.prod_name)을 URL용으로 안전하게 변환합니다.
safe_prod_name = urllib.parse.quote(self.prod_name)

view_url = f"https://{domain}/view?user={it.user.id}&product={safe_prod_name}"

# 버튼 생성 시 style을 반드시 link로 지정해주는 것이 좋습니다.
view_btn = ui.Button(
    label="제품보기", 
    url=view_url, 
    style=discord.ButtonStyle.link, # 이 줄을 추가하면 더 안정적입니다.
    emoji="<:shop:1481994009499930766>"
)
