<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>세일러 피스 - 인증</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #000; 
            color: #fff; 
            transition: background-color 0.3s, color 0.3s;
            min-h-screen: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* 라이트 모드 설정 */
        body.light-mode { background-color: #fff; color: #000; }

        /* 유리 박스 디자인 유지 */
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }

        body.light-mode .glass-card {
            background: rgba(0, 0, 0, 0.02);
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        }

        /* 입력창 디자인 유지 */
        .input-field {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            color: white;
            transition: all 0.2s;
        }
        body.light-mode .input-field { background-color: #f9f9f9; border-color: #ddd; color: black; }
        
        .input-field:focus { border-color: #666; outline: none; }

        /* 구분선 텍스트 가림 해결 (bg-inherit 사용) */
        .separator-text {
            background-color: inherit; /* 부모(유리박스)의 배경색을 그대로 따라감 */
            padding: 0 12px;
            z-index: 1;
        }

        .btn-discord { background-color: #5865F2; }
        .btn-discord:hover { background-color: #4752C4; }

        .hidden { display: none; }
        .fade-in { animation: fadeIn 0.3s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="p-4">

    <div class="absolute top-8 right-8 flex items-center space-x-6 z-20">
        <button onclick="toggleAuth()" id="nav-text" class="text-sm font-semibold text-gray-400 hover:text-white transition">회원가입</button>
        <button onclick="toggleTheme()" class="text-gray-400 hover:text-white transition">
            <i id="theme-icon" class="fa-solid fa-moon text-xl"></i>
        </button>
    </div>

    <div id="main-box" class="w-full max-w-md glass-card p-10 rounded-[32px] fade-in relative">
        
        <div id="login-section" class="space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">로그인 👋</h1>
                <p class="text-gray-400 text-sm">서비스를 이용하려면 로그인이 필요합니다.</p>
            </div>

            <button class="w-full btn-discord text-white font-bold py-4 rounded-xl flex items-center justify-center space-x-3 active:scale-95 transition">
                <i class="fa-brands fa-discord text-xl"></i>
                <span>디스코드로 로그인</span>
            </button>

            <div class="relative flex items-center justify-center">
                <div class="absolute inset-0 flex items-center">
                    <div class="w-full border-t border-gray-800 opacity-50"></div>
                </div>
                <span class="relative separator-text text-xs text-gray-500 font-medium">또는</span>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">아이디</label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-3.5">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호</label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-3.5 pr-12">
                    <button type="button" class="absolute right-4 top-10 text-gray-500"><i class="fa-regular fa-eye"></i></button>
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-xl hover:bg-gray-200 transition-all mt-2">
                    로그인 하기
                </button>
            </form>

            <div class="text-center pt-2">
                <button onclick="toggleAuth()" class="text-sm text-gray-400 hover:text-white">아직 계정이 없으신가요? <span class="font-bold underline ml-1">회원가입</span></button>
            </div>
        </div>

        <div id="signup-section" class="hidden space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">회원가입 👋</h1>
                <p class="text-gray-400 text-sm">새로운 계정을 생성하여 시작하세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">아이디 <span class="text-red-500">*</span></label>
                    <input type="text" placeholder="사용할 아이디" class="input-field w-full px-4 py-3.5">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 설정" class="input-field w-full px-4 py-3.5">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호 확인 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 재입력" class="input-field w-full px-4 py-3.5">
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-xl hover:bg-gray-200 transition-all mt-2">
                    계정 만들기
                </button>
            </form>

            <div class="text-center pt-2">
                <button onclick="toggleAuth()" class="text-sm text-gray-400 hover:text-white">이미 계정이 있으신가요? <span class="font-bold underline ml-1">로그인</span></button>
            </div>
        </div>
    </div>

    <script>
        let isLoginView = true;

        function toggleAuth() {
            const loginSec = document.getElementById('login-section');
            const signupSec = document.getElementById('signup-section');
            const navText = document.getElementById('nav-text');
            if (isLoginView) {
                loginSec.classList.add('hidden');
                signupSec.classList.remove('hidden');
                navText.innerText = '로그인';
            } else {
                signupSec.classList.add('hidden');
                loginSec.classList.remove('hidden');
                navText.innerText = '회원가입';
            }
            isLoginView = !isLoginView;
        }

        function toggleTheme() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            body.classList.toggle('light-mode');
            if (body.classList.contains('light-mode')) {
                icon.classList.replace('fa-moon', 'fa-sun');
            } else {
                icon.classList.replace('fa-sun', 'fa-moon');
            }
        }
    </script>
</body>
</html>
