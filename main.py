if __name__ == "__main__":
    print("로벅스 자동 판매 시작")
    Thread(target=run_fastapi, daemon=True).start()  # 포트 80 - 자동충전
    Thread(target=run_web, daemon=True).start()       # 포트 8080 - 웹
    bot.run(TOKEN)
