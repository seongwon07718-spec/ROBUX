<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>swnx - 접속</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
    <style>
        body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #121212; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; }
        .login-container { background-color: #1e1e1e; padding: 40px 30px; border-radius: 40px; width: 85%; max-width: 350px; text-align: center; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5); box-sizing: border-box; }
        h1 { color: #ffffff; font-size: 24px; margin-bottom: 30px; letter-spacing: 2px; }
        .input-group { position: relative; margin-bottom: 12px; }
        .input-group i { position: absolute; left: 18px; top: 50%; transform: translateY(-50%); color: #aaa; }
        .input-group input { width: 100%; padding: 14px 14px 14px 45px; background-color: #333; border: none; border-radius: 25px; color: white; font-size: 15px; box-sizing: border-box; outline: none; }
        .remember-me { display: flex; align-items: center; color: #ccc; font-size: 13px; margin: 15px 0 20px 5px; }
        .remember-me input { margin-right: 8px; cursor: pointer; }
        .cf-turnstile { margin-bottom: 20px; display: flex; justify-content: center; }
        .login-btn { background-color: #3498db; color: white; border: none; padding: 10px 40px; border-radius: 20px; font-size: 15px; font-weight: bold; cursor: pointer; transition: background 0.3s; width: 100%; }
        .login-btn:hover { background-color: #2980b9; }
        .forgot-link { display: block; margin-top: 18px; color: #3498db; text-decoration: none; font-size: 13px; cursor: pointer; }
        #signup-form { display: none; }
        .footer-text { position: absolute; bottom: 30px; color: #444; font-size: 13px; }
    </style>
</head>
<body>

    <div class="login-container">
        <div id="login-box">
            <h1>로그인</h1>
            <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" id="login-id" placeholder="사용자 아이디" required>
            </div>
            <div class="input-group">
                <i class="fas fa-lock"></i>
                <input type="password" id="login-pw" placeholder="비밀번호" required>
            </div>
            <div class="remember-me">
                <input type="checkbox" id="rem">
                <label for="rem">로그인 상태 유지</label>
            </div>
            <div class="cf-turnstile" data-sitekey="0x4AAAAAAACJuAjiUyHT8jhqw"></div>
            <button onclick="handleLogin()" class="login-btn">로그인</button>
            <a onclick="toggleForm('signup')" class="forgot-link">계정이 없으신가요?</a>
        </div>

        <div id="signup-form">
            <h1>회원가입</h1>
            <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" id="sign-id" placeholder="사용할 아이디" required>
            </div>
            <div class="input-group">
                <i class="fas fa-lock"></i>
                <input type="password" id="sign-pw" placeholder="비밀번호 설정" required>
            </div>
            <div class="input-group">
                <i class="fas fa-check-double"></i>
                <input type="password" id="sign-pw-check" placeholder="비밀번호 확인" required>
            </div>
            <button onclick="handleSignup()" class="login-btn">가입 완료</button>
            <a onclick="toggleForm('login')" class="forgot-link">이미 계정이 있으신가요?</a>
        </div>
    </div>

    <div class="footer-text">swnx.shop</div>

    <script>
        // 화면 전환 함수
        function toggleForm(type) {
            document.getElementById('login-box').style.display = type === 'signup' ? 'none' : 'block';
            document.getElementById('signup-form').style.display = type === 'signup' ? 'block' : 'none';
        }

        // 회원가입 전송
        async function handleSignup() {
            const id = document.getElementById('sign-id').value;
            const pw = document.getElementById('sign-pw').value;
            const pwCheck = document.getElementById('sign-pw-check').value;

            if (!id || !pw) return alert("아이디와 비밀번호를 입력하세요.");
            if (pw !== pwCheck) return alert("비밀번호가 일치하지 않습니다.");

            const res = await fetch('/api/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, pw })
            });
            const data = await res.json();
            alert(data.msg);
            if (res.ok) toggleForm('login');
        }

        // 로그인 전송
        async function handleLogin() {
            const id = document.getElementById('login-id').value;
            const pw = document.getElementById('login-pw').value;

            if (!id || !pw) return alert("아이디와 비밀번호를 입력하세요.");

            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, pw })
            });
            const data = await res.json();
            alert(data.msg);
            if (data.success) window.location.href = "https://naver.com";
        }
    </script>
</body>
</html>
