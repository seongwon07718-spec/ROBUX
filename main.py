@app.get("/view")
async def view_product(key: str = None):
    if not key:
        return HTMLResponse(content="<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>잘못된 접근입니다.</h2></body>")

    try:
        conn = sqlite3.connect('vending_data.db', timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT product_name, stock_data FROM buy_log WHERE web_key = ?", (key,))
        res = cur.fetchone()
        conn.close()
    except Exception as e:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;'><h2>데이터베이스 오류</h2></body>")
    
    if not res:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>데이터를 찾을 수 없습니다.</h2></body>")

    prod_name, stock_data = res

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>구매 정보 확인</title>
        <style>
            @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
            
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                background-color: #0a0a0a; 
                color: #ffffff; 
                font-family: 'Pretendard', sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                width: 100%;
            }}
            .container {{ 
                width: 90%; 
                max-width: 450px; 
                background: #141414;
                padding: 40px 30px; 
                border-radius: 30px; /* 외곽 컨테이너 둥글게 */
                text-align: center; 
                border: 1px solid #222;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            }}
            h1 {{ 
                font-size: 24px; 
                font-weight: 700; 
                margin-bottom: 25px;
                word-break: break-all;
            }}
            .stock-label {{
                font-size: 13px;
                color: #888;
                margin-bottom: 15px;
                display: block;
            }}
            .stock-box {{ 
                background: #1f1f1f; 
                padding: 25px; 
                border-radius: 20px; /* 내부 박스 둥글게 */
                border: 1px solid #333; 
                text-align: center; 
                font-family: 'Pretendard', sans-serif; 
                white-space: pre-wrap; 
                word-break: break-all; 
                margin-bottom: 30px; 
                color: #efefef; 
                font-size: 16px; 
                line-height: 1.6;
            }}
            .copy-btn {{ 
                background: #ffffff; 
                color: #000000; 
                border: none; 
                padding: 16px 0; 
                width: 100%; 
                font-size: 15px; 
                font-weight: 700; 
                border-radius: 15px; /* 버튼 둥글게 */
                cursor: pointer; 
                transition: all 0.2s ease; 
            }}
            .copy-btn:hover {{ 
                background: #e0e0e0; 
            }}
            .copy-btn:active {{
                transform: scale(0.97);
            }}

            @media (max-width: 480px) {{
                .container {{ padding: 35px 20px; }}
                h1 {{ font-size: 22px; }}
                .stock-box {{ font-size: 15px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{prod_name}</h1>
            
            <span class="stock-label">상품 정보</span>
            <div class="stock-box" id="stockContent">{stock_data}</div>
            
            <button class="copy-btn" id="copyBtn" onclick="copyToClipboard()">텍스트 복사하기</button>
        </div>

        <script>
            function copyToClipboard() {{
                const content = document.getElementById('stockContent').innerText;
                const btn = document.getElementById('copyBtn');
                
                const tempTextArea = document.createElement('textarea');
                tempTextArea.value = content;
                document.body.appendChild(tempTextArea);
                tempTextArea.select();
                
                try {{
                    document.execCommand('copy');
                    btn.innerText = '복사 완료';
                    btn.style.background = '#444';
                    btn.style.color = '#fff';
                    setTimeout(() => {{
                        btn.innerText = '텍스트 복사하기';
                        btn.style.background = '#ffffff';
                        btn.style.color = '#000000';
                    }}, 1500);
                }} catch (err) {{
                    alert('복사에 실패했습니다.');
                }} finally {{
                    document.body.removeChild(tempTextArea);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
