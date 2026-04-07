# 상단에 추가
from fastapi.responses import HTMLResponse

# run_fastapi 수정
def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)  # ✅ 88 → 8080
