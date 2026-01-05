import sqlite3
import json
import os

def save_verified_user(discord_id, discord_name, roblox_name, roblox_id):
    # SQLite DB 저장
    conn = sqlite3.connect('betting_history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS verified_users 
        (discord_id INTEGER PRIMARY KEY, discord_name TEXT, roblox_name TEXT, roblox_id TEXT)''')
    cursor.execute('INSERT OR REPLACE INTO verified_users VALUES (?, ?, ?, ?)',
                   (discord_id, discord_name, roblox_name, str(roblox_id)))
    conn.commit()
    conn.close()

    # JSON 파일 저장 (베팅 봇 조회용 호환성 유지)
    file_path = "verified_users.json"
    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: data = {}
    
    data[str(discord_id)] = str(roblox_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_bet_info(bet_id, c_id, c_rid, p_id, p_rid, result):
    conn = sqlite3.connect('betting_history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS bets 
        (bet_id TEXT PRIMARY KEY, c_discord_id INTEGER, c_roblox_id TEXT, 
         p_discord_id INTEGER, p_roblox_id TEXT, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('INSERT INTO bets (bet_id, c_discord_id, c_roblox_id, p_discord_id, p_roblox_id, result) VALUES (?, ?, ?, ?, ?, ?)',
                   (bet_id, c_id, str(c_rid), p_id, str(p_rid), result))
    conn.commit()
    conn.close()

def load_db(): # 기존 함수 유지
    conn = sqlite3.connect('betting_history.db')
    cursor = conn.cursor()
    cursor.execute('SELECT discord_name, roblox_name FROM verified_users')
    rows = cursor.fetchall()
    conn.close()
    return [{"discord_name": r[0], "roblox_name": r[1]} for r in rows]
