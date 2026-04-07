import os

@web_app.get("/purchase-log")
async def purchase_log_page():
    try:
        # main.py 와 같은 폴더에서 찾기
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "purchase_log.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>오류: {e}</h1>")
