from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import requests
import os

app = Flask(__name__)
app.secret_key = "sailor_peace_secret_key" # 세션 암호화 키

# [3번] SQLite DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# 유저 테이블 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=True) # [4번] 암호화된 비번
    discord_id = db.Column(db.String(100), unique=True, nullable=True) # [2번] 디스코드 ID

# DB 생성
with app.app_context():
    db.create_all()

# [2번] 디스코드 설정 (성원님이 발급받은 정보를 여기에 넣으세요)
CLIENT_ID = '여기에_클라이언트_ID_입력'
CLIENT_SECRET = '여기에_클라이언트_시크릿_입력'
REDIRECT_URI = 'http://127.0.0.1:5000/discord/callback'

@app.route('/')
def home():
    return render_template('index.html')

# [1번 & 4번] 일반 회원가입
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

# [1번] 일반 로그인
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password and bcrypt.check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({"success": True, "message": f"{user.username}님 환영합니다!"})
    return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀립니다."})

# [2번] 디스코드 인증 시작
@app.route('/login/discord')
def discord_login():
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(url)

# [2번] 디스코드 콜백 처리 (실제 구현)
@app.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    
    # 1. Access Token 요청
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    token_response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    access_token = token_response.json().get('access_token')

    # 2. 유저 정보 요청
    user_headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get('https://discord.com/api/users/@me', headers=user_headers)
    user_info = user_response.json()
    
    discord_id = user_info.get('id')
    discord_name = user_info.get('username')

    # 3. DB 저장 및 로그인 처리
    user = User.query.filter_by(discord_id=discord_id).first()
    if not user:
        user = User(username=discord_name, discord_id=discord_id)
        db.session.add(user)
        db.session.commit()
    
    session['user_id'] = user.id
    return f"<h1>{discord_name}님, 디스코드 로그인 성공!</h1><a href='/'>홈으로 돌아가기</a>"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
