<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>login</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #121212;
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
        }

        /* 로그인 박스: 모바일에서 꽉 차지 않게 width 85%와 max-width 설정 */
        .login-container {
            background-color: #1e1e1e;
            padding: 40px 30px;
            border-radius: 40px;
            width: 85%;
            max-width: 350px; /* 기존 380px에서 살짝 줄여 더 깔끔하게 조절 */
            text-align: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
            box-sizing: border-box;
        }

        h1 {
            color: #ffffff;
            font-size: 24px;
            margin-bottom: 30px;
            letter-spacing: 2px;
        }

        .input-group {
            position: relative;
            margin-bottom: 12px;
        }

        .input-group i {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            color: #aaa;
        }

        .input-group input {
            width: 100%;
            padding: 14px 14px 14px 45px;
            background-color: #333;
            border: none;
            border-radius: 25px;
            color: white;
            font-size: 15px;
            box-sizing: border-box;
            outline: none;
        }

        .remember-me {
            display: flex;
            align-items: center;
            color: #ccc;
            font-size: 13px;
            margin: 15px 0 20px 5px;
        }

        .remember-me input {
            margin-right: 8px;
            cursor: pointer;
        }

        /* 캡차(Turnstile) 중앙 정렬 및 여백 */
        .cf-turnstile {
            margin-bottom: 20px;
            display: flex;
            justify-content: center;
        }

        .login-btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 40px;
            border-radius: 20px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }

        .login-btn:hover {
            background-color: #2980b9;
        }

        .forgot-link {
            display: block;
            margin-top: 18px;
            color: #3498db;
            text-decoration: none;
            font-size: 13px;
        }

        .footer-text {
            position: absolute;
            bottom: 30px;
            color: #444;
            font-size: 13px;
        }
    </style>
</head>
<body>

    <div class="login-container">
        <h1>로그인</h1>
        
        <form action="#">
            <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" placeholder="사용자 아이디" required>
            </div>
            
            <div class="input-group">
                <i class="fas fa-lock"></i>
                <input type="password" placeholder="비밀번호" required>
            </div>

            <div class="remember-me">
                <input type="checkbox" id="rem">
                <label for="rem">로그인 상태 유지</label>
            </div>

            <div class="cf-turnstile" data-sitekey="0x4AAAAAAACJuAjiUyHT8jhqw"></div>

            <button type="submit" class="login-btn">로그인</button>
            
            <a href="#" class="forgot-link">계정이 없으신가요?</a>
        </form>
    </div>

</body>
</html>
