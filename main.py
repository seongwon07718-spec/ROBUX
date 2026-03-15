@app.get("/view")
async def view_product(key: str):
    conn = sqlite3.connect('vending_data.db', timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT product_name, stock_data FROM buy_log WHERE web_key = ?", (key,))
    res = cur.fetchone()
    conn.close()
    
    if not res:
        return HTMLResponse(content="<h1 style='color:white; text-align:center;'>잘못된 접근이거나 만료된 페이지입니다.</h1>", status_code=403)

    prod_name, stock_data = res
    # 자바스크립트를 이용한 복사 기능 포함
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>구매 확인</title>
        <style>
            body {{ background-color: #0f0f12; color: #ffffff; font-family: 'Pretendard', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: #1c1c21; padding: 30px; border-radius: 20px; border: 1px solid #333; width: 90%; max-width: 400px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            h2 {{ color: #7289da; margin-bottom: 20px; font-size: 24px; }}
            .stock-box {{ background: #09090b; padding: 15px; border-radius: 12px; border: 1px solid #444; text-align: left; font-family: monospace; white-space: pre-wrap; word-break: break-all; margin-bottom: 20px; max-height: 200px; overflow-y: auto; color: #ccc; }}
            .copy-btn {{ background: #5865f2; color: white; border: none; padding: 12px 25px; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; width: 100%; }}
            .copy-btn:hover {{ background: #4752c4; }}
            .copy-btn:active {{ transform: scale(0.98); }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>📦 {prod_name}</h2>
            <div class="stock-box" id="stockContent">{stock_data}</div>
            <button class="copy-btn" onclick="copyToClipboard()">재고 복사하기</button>
        </div>

        <script>
            function copyToClipboard() {{
                const content = document.getElementById('stockContent').innerText;
                navigator.clipboard.writeText(content).then(() => {{
                    const btn = document.querySelector('.copy-btn');
                    btn.innerText = '✅ 복사 완료!';
                    btn.style.background = '#43b581';
                    setTimeout(() => {{
                        btn.innerText = '재고 복사하기';
                        btn.style.background = '#5865f2';
                    }}, 2000);
                }}).catch(err => {{
                    alert('복사 실패: ' + err);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
