@app.get("/view")
async def view_product(key: str = None):
    if not key:
        return HTMLResponse(content="<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>ACCESS DENIED</h2></body>")

    try:
        conn = sqlite3.connect('vending_data.db', timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT product_name, stock_data FROM buy_log WHERE web_key = ?", (key,))
        res = cur.fetchone()
        conn.close()
    except Exception as e:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;'><h2>DATABASE ERROR</h2></body>")
    
    if not res:
        return HTMLResponse(content=f"<body style='background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;'><h2>DATA NOT FOUND</h2></body>")

    prod_name, stock_data = res

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Order Detail</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
            
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                background-color: #000000; 
                color: #ffffff; 
                font-family: 'Inter', -apple-system, sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                width: 100%;
            }}
            .container {{ 
                width: 100%; 
                max-width: 500px; 
                padding: 40px 20px; 
                text-align: center; 
            }}
            .header {{ 
                margin-bottom: 40px; 
            }}
            h1 {{ 
                font-size: 28px; 
                font-weight: 700; 
                letter-spacing: -1px; 
                margin-bottom: 10px;
                text-transform: uppercase;
            }}
            .divider {{
                width: 40px;
                height: 2px;
                background-color: #ffffff;
                margin: 0 auto 20px auto;
            }}
            .stock-label {{
                font-size: 12px;
                color: #666666;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 15px;
            }}
            .stock-box {{ 
                background: #000000; 
                padding: 25px; 
                border-radius: 0px; 
                border: 1px solid #ffffff; 
                text-align: center; 
                font-family: 'Consolas', monospace; 
                white-space: pre-wrap; 
                word-break: break-all; 
                margin-bottom: 40px; 
                color: #ffffff; 
                font-size: 16px; 
                line-height: 1.6;
            }}
            .copy-btn {{ 
                background: #ffffff; 
                color: #000000; 
                border: none; 
                padding: 18px 0; 
                width: 100%; 
                font-size: 14px; 
                font-weight: 700; 
                text-transform: uppercase; 
                letter-spacing: 1px; 
                cursor: pointer; 
                transition: all 0.3s ease; 
            }}
            .copy-btn:hover {{ 
                background: #cccccc; 
            }}
            .copy-btn:active {{
                transform: scale(0.99);
            }}

            /* 모바일 대응 */
            @media (max-width: 480px) {{
                .container {{ padding: 30px 25px; }}
                h1 {{ font-size: 24px; }}
                .stock-box {{ font-size: 14px; padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{prod_name}</h1>
                <div class="divider"></div>
            </div>
            
            <div class="stock-label">Information</div>
            <div class="stock-box" id="stockContent">{stock_data}</div>
            
            <button class="copy-btn" id="copyBtn" onclick="copyToClipboard()">Copy Text</button>
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
                    btn.innerText = 'Copied Successfully';
                    btn.style.background = '#333333';
                    btn.style.color = '#ffffff';
                    setTimeout(() => {{
                        btn.innerText = 'Copy Text';
                        btn.style.background = '#ffffff';
                        btn.style.color = '#000000';
                    }}, 2000);
                }} catch (err {{
                    alert('Copy failed');
                }} finally {{
                    document.body.removeChild(tempTextArea);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
