# app.py의 로그인 API 부분
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password and bcrypt.check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        # 로그인 성공 시 리다이렉트할 주소를 프론트엔드에 전달
        return jsonify({"success": True, "message": "성공!", "redirect": url_for('main_page')})
    return jsonify({"success": False, "message": "실패!"})

# 메인 페이지 라우트 추가
@app.route('/main')
def main_page():
    if 'user_id' not in session:
        return redirect(url_for('home')) # 로그인 안됐으면 다시 로그인창으로
    return render_template('main.html')
