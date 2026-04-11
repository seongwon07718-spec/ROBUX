from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 메인 상점 페이지
@app.route('/')
def index():
    return render_template('main.html')

# 1단계: 입금 정보 입력 페이지
@app.route('/change')
def change():
    return render_template('change.html')

# 2단계: 계좌 정보 표시 API (POST로 데이터를 받음)
@app.route('/change/api', methods=['POST'])
def change_api():
    depositor = request.form.get('depositor')
    amount = request.form.get('amount')
    
    # 예금주와 계좌번호 설정
    bank_info = {
        "owner": "정성원",
        "bank": "카카오뱅크",
        "account": "3333-01-2345678"
    }
    
    return render_template('change_api.html', 
                           depositor=depositor, 
                           amount=amount, 
                           bank=bank_info)

if __name__ == '__main__':
    app.run(debug=True)
