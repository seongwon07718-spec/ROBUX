from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
DATABASE = "robux_shop.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gift_queue (
                order_id TEXT PRIMARY KEY,
                target_id INTEGER,
                pass_id INTEGER,
                status TEXT DEFAULT 'processing'
            )
        """)
init_db()

@app.route('/get_latest_order', methods=['GET'])
def get_order():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT order_id, target_id, pass_id FROM gift_queue WHERE status = 'processing' ORDER BY rowid DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            return jsonify({"order_id": row[0], "target_id": row[1], "pass_id": row[2]})
    return jsonify({"error": "no orders"}), 404

@app.route('/complete_order', methods=['GET', 'POST'])
def complete_order():
    order_id = request.args.get('order_id') or (request.json.get('order_id') if request.is_json else None)
    status = request.args.get('status') or (request.json.get('status') if request.is_json else None)
    
    if not order_id or not status:
        return jsonify({"error": "missing data"}), 400

    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE gift_queue SET status = ? WHERE order_id = ?", (status, order_id))
        conn.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
