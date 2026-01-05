import sqlite3

def save_bet_info(bet_id, creator_id, participant_id, result):
    conn = sqlite3.connect('betting_history.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS bets 
        (bet_id TEXT PRIMARY KEY, creator_id INTEGER, participant_id INTEGER, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('INSERT INTO bets (bet_id, creator_id, participant_id, result) VALUES (?, ?, ?, ?)',
                   (bet_id, creator_id, participant_id, result))
    conn.commit()
    conn.close()
