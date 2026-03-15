import multiprocessing
import asyncio
import uvicorn

# ... (기존 app 정의 및 봇 설정 코드들) ...

def run_web():
    # 웹 서버 실행 (88번 포트)
    uvicorn.run(app, host="0.0.0.0", port=88)

async def run_bot():
    token = "YOUR_BOT_TOKEN_HERE" # 봇 토큰 입력
    # DONE SYNC COMMANDS 로그가 뜬다면 이미 토큰 설정이 어딘가 되어있을 수도 있습니다.
    await bot.start(token)

if __name__ == "__main__":
    # 1. DB 초기화
    init_db()
    
    # 2. 웹 서버 프로세스 시작
    web_p = multiprocessing.Process(target=run_web)
    web_p.start()
    
    # 3. 메인 프로세스에서 봇 실행
    try:
        asyncio.run(run_bot()) 
    except KeyboardInterrupt:
        print("프로그램 종료 중...")
        web_p.terminate()
