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
                    status TEXT DEFAULT 'processing',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    init_db()


    # Lua 스크립트가 주문 가져가는 엔드포인트
    @app.route('/get_latest_order', methods=['GET'])
    def get_order():
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT order_id, target_id, pass_id
                FROM gift_queue
                WHERE status = 'processing'
                ORDER BY rowid ASC
                LIMIT 1
            """)
            row = cur.fetchone()

        if row:
            return jsonify({
                "order_id": row[0],
                "target_id": row[1],
                "pass_id":   row[2]
            })

        return jsonify({"error": "no orders"}), 404


    # Lua 스크립트가 결과 보고하는 엔드포인트 (GET만 사용 - HttpGet 호환)
    @app.route('/complete_order', methods=['GET'])
    def complete_order():
        order_id = request.args.get('order_id')
        status   = request.args.get('status')

        if not order_id or not status:
            return jsonify({"error": "missing data"}), 400

        if status not in ('completed', 'failed'):
            return jsonify({"error": "invalid status"}), 400

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE gift_queue SET status = ? WHERE order_id = ?",
                (status, order_id)
            )
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "order not found"}), 404

        return jsonify({"success": True})


    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000, debug=False)
