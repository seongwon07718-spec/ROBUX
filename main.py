1) 가상환경(권장) 생성
   python -m venv venv
   source venv/bin/activate (Linux/macOS) 또는 venv\Scripts\activate (Windows)

2) 패키지 설치
   pip install -r requirements.txt

3) DB 초기화 (한 번만)
   python init_db.py

4) 봇 실행
   python bot.py

5) DB 확인
   python db_to_json.py   -> db.json 생성 (편리하게 확인 가능)
