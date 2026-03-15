# 1. 윈도우 환경 에러 방지를 위해 실행 함수를 따로 뺍니다.
def run_web():
    uvicorn.run(app, host="0.0.0.0", port=88)

if __name__ == "__main__":
    # 기존 Thread 실행은 유지
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # 2. lambda 대신 run_web 함수를 사용하고, 바로 종료(terminate)되지 않게 수정
    web_p = multiprocessing.Process(target=run_web)
    web_p.start()
    
    # [수정] web_p.terminate()를 여기서 하면 서버가 바로 꺼지므로 삭제했습니다.

    # 3. 봇 실행
    bot.run("MTQ3NzY2Mjg3MTIwNTcxMjA3OQ.GvFnzw.qMYsMr_-LODzECKnYY")
