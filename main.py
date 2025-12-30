export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // [서버 로직] 1. 회원가입 데이터 저장
    if (request.method === "POST" && url.pathname === "/api/signup") {
      const { id, pw } = await request.json();
      // 중복 체크
      const exists = await env.USERS.get(id);
      if (exists) return new Response(JSON.stringify({ msg: "이미 존재하는 아이디입니다." }), { status: 400 });
      
      await env.USERS.put(id, pw);
      return new Response(JSON.stringify({ msg: "회원가입이 완료되었습니다!" }));
    }

    // [서버 로직] 2. 로그인 데이터 확인
    if (request.method === "POST" && url.pathname === "/api/login") {
      const { id, pw } = await request.json();
      const storedPw = await env.USERS.get(id);
      
      if (storedPw === pw) {
        return new Response(JSON.stringify({ success: true, msg: "로그인 성공!" }));
      } else {
        return new Response(JSON.stringify({ success: false, msg: "아이디 또는 비밀번호를 확인하세요." }), { status: 401 });
      }
    }

    // [화면 로직] 3. HTML 렌더링
    return new Response(`
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>swnx - 접속</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
    <style>
        body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #121212; font-family: 'Apple SD Gothic Neo', sans-serif; }
        .login-container { background-color: #1e1e1e; padding: 40px 30px; border-radius: 40px; width: 85%; max-width: 350px; text-align: center; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5); box-sizing: border-box; }
        h1 { color: #ffffff; font-size: 24px; margin-bottom: 30px; letter-spacing: 2px; }
        .input-group { position: relative; margin-bottom: 12px; }
        .input-group i { position: absolute; left: 18px; top: 50%; transform: translateY(-50%); color: #aaa; }
        .input-group input { width: 100%; padding: 14px 14px 14px 45px; background-color: #333; border: none; border-radius: 25px; color: white; font-size: 15px; box-sizing: border-box; outline: none; }
        .cf-turnstile { margin-bottom: 20px; display: flex; justify-content: center; }
        .login-btn { background-color: #3498db; color: white; border: none; padding: 10px 40px; border-radius: 20px; font-size: 15px; font-weight: bold; cursor: pointer; transition: background 0.3s; width: 150px; }
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
            <div class="input-group"><i class="fas fa-user"></i><input type="text" id="l-id" placeholder="사용자 아이디"></div>
            <div class="input-group"><i class="fas fa-lock"></i><input type="password" id="l-pw" placeholder="비밀번호"></div>
            <div class="cf-turnstile" data-sitekey="0x4AAAAAAACJuAjiUyHT8jhqw"></div>
            <button onclick="handleLogin()" class="login-btn">로그인</button>
            <a onclick="toggleForm('signup')" class="forgot-link">계정이 없으신가요?</a>
        </div>

        <div id="signup-form">
            <h1>회원가입</h1>
            <div class="input-group"><i class="fas fa-user"></i><input type="text" id="s-id" placeholder="사용할 아이디"></div>
            <div class="input-group"><i class="fas fa-envelope"></i><input type="email" placeholder="이메일 주소"></div>
            <div class="input-group"><i class="fas fa-lock"></i><input type="password" id="s-pw" placeholder="비밀번호 설정"></div>
            <button onclick="handleSignup()" class="login-btn">가입 완료</button>
            <a onclick="toggleForm('login')" class="forgot-link">이미 계정이 있으신가요?</a>
        </div>
    </div>
    <div class="footer-text">swnx.shop</div>

    <script>
        function toggleForm(type) {
            document.getElementById('login-box').style.display = type === 'signup' ? 'none' : 'block';
            document.getElementById('signup-form').style.display = type === 'signup' ? 'block' : 'none';
        }

        async function handleSignup() {
            const id = document.getElementById('s-id').value;
            const pw = document.getElementById('s-pw').value;
            if(!id || !pw) return alert("필드를 채워주세요.");

            const res = await fetch('/api/signup', {
                method: 'POST',
                body: JSON.stringify({ id, pw })
            });
            const data = await res.json();
            alert(data.msg);
            if(res.ok) toggleForm('login');
        }

        async function handleLogin() {
            const id = document.getElementById('l-id').value;
            const pw = document.getElementById('l-pw').value;

            const res = await fetch('/api/login', {
                method: 'POST',
                body: JSON.stringify({ id, pw })
            });
            const data = await res.json();
            alert(data.msg);
            if(data.success) {
                // 로그인 성공 시 이동할 주소 (예: 네이버)
                window.location.href = "https://swnx.shop/main"; 
            }
        }
    </script>
</body>
</html>
    `, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  }
};
