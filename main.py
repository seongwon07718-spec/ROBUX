<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Page</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* 기본 배경 설정 */
        body {
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #121212; /* 어두운 배경색 */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* 메인 로그인 박스 */
        .login-container {
            background-color: #1e1e1e;
            padding: 50px 40px;
            border-radius: 40px; /* 둥근 모서리 */
            width: 380px;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
        }

        h1 {
            color: #ffffff;
            font-size: 28px;
            margin-bottom: 35px;
            letter-spacing: 2px;
        }

        /* 입력창 그룹 (아이콘 + 인풋) */
        .input-group {
            position: relative;
            margin-bottom: 15px;
        }

        .input-group i {
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #aaa;
        }

        .input-group input {
            width: 100%;
            padding: 15px 15px 15px 50px;
            background-color: #333;
            border: none;
            border-radius: 25px;
            color: white;
            font-size: 16px;
            box-sizing: border-box; /* 패딩 포함 너비 계산 */
            outline: none;
        }

        /* 체크박스 영역 */
        .remember-me {
            display: flex;
            align-items: center;
            color: #ccc;
            font-size: 14px;
            margin: 15px 0 25px 5px;
        }

        .remember-me input {
            margin-right: 10px;
            cursor: pointer;
        }

        /* 로그인 버튼 */
        .login-btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 35px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }

        .login-btn:hover {
            background-color: #2980b9;
        }

        /* 비밀번호 찾기 링크 */
        .forgot-link {
            display: block;
            margin-top: 20px;
            color: #3498db;
            text-decoration: none;
            font-size: 13px;
        }

        .forgot-link:hover {
            text-decoration: underline;
        }

        /* 하단 도메인 텍스트 */
        .footer-text {
            position: absolute;
            bottom: 30px;
            color: #555;
            font-size: 14px;
        }
    </style>
</head>
<body>

    <div class="login-container">
        <h1>LOGIN</h1>
        
        <form action="#">
            <div class="input-group">
                <i class="fas fa-user"></i>
                <input type="text" placeholder="Username" required>
            </div>
            
            <div class="input-group">
                <i class="fas fa-lock"></i>
                <input type="password" placeholder="Password" required>
            </div>

            <div class="remember-me">
                <input type="checkbox" id="rem">
                <label for="rem">Remember me</label>
            </div>

            <button type="submit" class="login-btn">LOGIN</button>
            
            <a href="#" class="forgot-link">Forgot your password?</a>
        </form>
    </div>

    <div class="footer-text">swnx.shop</div>

</body>
</html>
