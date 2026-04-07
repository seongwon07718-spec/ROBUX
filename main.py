@web_app.get("/purchase-log")
async def purchase_log_page():
    try:
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purchase_log.html")
        print(f"[웹] HTML 경로: {html_path}")
        print(f"[웹] 파일 존재: {os.path.exists(html_path)}")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        return HTMLResponse(f"<h1>오류: {e}</h1>")
