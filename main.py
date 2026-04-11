from flask import Flask, render_template, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # 세션 보안키

# [3번] SQLite DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# 유저 테이블 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True) # [4번] 암호화된 비번
    discord_id = db.Column(db.String(100), unique=True, nullable=True) # [2번] 디스코드 ID

# DB 생성
with app.app_context():
    db.create_all()

# [2번] 디스코드 설정 (성원님의 정보를 입력하세요)
CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
REDIRECT_URI = 'http://127.0.0.1:5000/discord/callback'

@app.route('/')
def home():
    return render_template('index.html')

# [1번 & 4번] 회원가입 로직
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."})
    
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "회원가입 성공!"})

# [1번] 로그인 로직
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({"success": True, "message": "로그인 성공!"})
    return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀립니다."})

# [2번] 디스코드 로그인 시작
@app.route('/login/discord')
def discord_login():
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(url)

@app.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    # 실제 구현 시 여기서 코드를 토큰으로 교환하고 유저 정보를 가져와 DB에 저장하는 로직이 들어갑니다.
    return "디스코드 인증 완료! (서버 연결 성공)"

if __name__ == '__main__':
    app.run(port=5000, debug=True)
