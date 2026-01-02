import json
import os

DB_FILE = "verified_users.json"

# DB 초기화 및 로드 함수
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# 유저 저장 함수 (비동기)
async def save_verified_user(user_id, discord_name, roblox_name):
    db = load_db()
    
    # 중복 저장 방지 및 정보 업데이트
    found = False
    for user in db:
        if user['discord_id'] == user_id:
            user['discord_name'] = discord_name # 디스코드 이름 업데이트
            user['roblox_name'] = roblox_name   # 로블록스 이름 업데이트
            found = True
            break
            
    if not found:
        db.append({
            "discord_id": user_id,
            "discord_name": discord_name,
            "roblox_name": roblox_name
        })
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
