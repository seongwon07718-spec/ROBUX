# --- [추가] 웹 서버 로직 ---
app = FastAPI()

@app.get("/view")
async def view_product(key: str): # 보안 키로만 조회 가능
    conn = sqlite3.connect('vending_data.db', timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT product_name, stock_data FROM buy_log WHERE web_key = ?", (key,))
    res = cur.fetchone()
    conn.close()
    
    if not res:
        return HTMLResponse(content="<h1 style='color:white;'>권한이 없거나 잘못된 접근입니다.</h1>", status_code=403)

    prod_name, stock_data = res
    formatted_data = stock_data.replace('\n', '<br>')

    return HTMLResponse(content=f"""
        <body style="background-color: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding-top: 50px;">
            <div style="display: inline-block; background: #2a2a2a; padding: 30px; border-radius: 15px; border: 1px solid #444;">
                <h2 style="color: #7289da;">📦 {prod_name}</h2>
                <div style="background: #111; padding: 20px; border-radius: 8px; text-align: left; font-family: monospace;">
                    {formatted_data}
                </div>
            </div>
        </body>
    """)

# --- [수정] 메인 실행부 ---
if __name__ == "__main__":
    init_db() # DB 초기화 확인
    
    # 웹 서버 프로세스 별도 시작 (88번 포트)
    web_p = multiprocessing.Process(target=lambda: uvicorn.run(app, host="0.0.0.0", port=88))
    web_p.start()
    
    try:
        asyncio.run(run_bot()) # 봇 실행 함수 이름에 맞춰 수정 (예: run_bot 또는 bot.start)
    except KeyboardInterrupt:
        web_p.terminate()
