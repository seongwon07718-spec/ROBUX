from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import sqlite3
import uvicorn

app = FastAPI()

@app.get("/view")
async def view_product(id: int):
    # DB 연결 (timeout 설정으로 자충 서버와 충돌 방지)
    conn = sqlite3.connect('vending_data.db', timeout=10)
    cur = conn.cursor()
    
    # 구매 로그에서 해당 구매 내역의 제품명과 재고 원문 데이터를 가져옴
    cur.execute("SELECT product_name, stock_data FROM buy_log WHERE id = ?", (id,))
    res = cur.fetchone()
    conn.close()
    
    if not res:
        return HTMLResponse(content="<h1 style='color:white;'>구매 정보를 찾을 수 없습니다.</h1>", status_code=404)

    prod_name, raw_stock_data = res

    # 웹 화면 구성
    return HTMLResponse(content=f"""
        <html>
            <head>
                <meta charset="utf-8">
                <title>제품 확인</title>
                <style>
                    body {{ background-color: #1a1c1e; color: #ffffff; font-family: 'Malgun Gothic', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .card {{ background: #2f3136; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 80%; max-width: 500px; border: 1px solid #4f545c; }}
                    h2 {{ color: #7289da; border-bottom: 1px solid #4f545c; padding-bottom: 15px; margin-top: 0; }}
                    .stock-box {{ background: #202225; padding: 20px; border-radius: 8px; border: 1px solid #202225; font-family: 'Consolas', monospace; white-space: pre-wrap; word-break: break-all; color: #dcddde; line-height: 1.6; }}
                    .label {{ font-size: 0.9em; color: #b9bbbe; margin-bottom: 8px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>📦 {prod_name}</h2>
                    <div class="label">구매하신 재고 내용:</div>
                    <div class="stock-box">{raw_stock_data}</div>
                    <p style="font-size: 0.8em; color: #72767d; margin-top: 20px; text-align: center;">이 페이지는 본인만 확인 가능합니다.</p>
                </div>
            </body>
        </html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=88)
