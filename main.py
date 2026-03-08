# main.py 맨 밑부분
if __name__ == "__main__":
    # 백그라운드에서 ios_charge 서버 실행 로직을 넣거나,
    # 그냥 편하게 터미널 두 개(main.py용, ios_charge.py용)를 띄워두는 게 디버깅하기엔 제일 좋습니다.
    bot.run("너의_봇_토큰")


# ios_charge.py 파일의 가장 아랫부분에 넣어주세요
if __name__ == "__main__":
    import uvicorn
    # 88번 포트로 서버를 실행합니다.
    uvicorn.run(app, host="0.0.0.0", port=88)
