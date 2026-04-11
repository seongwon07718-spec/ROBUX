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
        
        /* 기본 상태 (다크 모드) */
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #000; 
            color: #fff; 
            transition: background-color 0.3s, color 0.3s;
            overflow: hidden; 
        }

        /* 라이트 모드 스타일 */
        body.light-mode {
            background-color: #ffffff;
            color: #000;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.7);
            transition: all 0.3s;
        }

        /* 라이트 모드에서의 유리 박스 및 텍스트 설정 */
        body.light-mode .glass-card {
            background: rgba(0, 0, 0, 0.03);
            border: 1px solid rgba(0, 0, 0, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        }
        body.light-mode .text-gray-400 { color: #666; }
        body.light-mode .input-field { background-color: #f5f5f5; border-color: #ddd; color: #000; }
        body.light-mode button.bg-white { background-color: #000; color: #fff; }

        .input-field {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            transition: all 0.2s ease;
        }
        .input-field:focus { border-color: #555; outline: none; background-color: #222; }

        .btn-discord { background-color: #5865F2; transition: background-color 0.2s; }
        .btn-discord:hover { background-color: #4752C4; }

        .fade-in { animation: fadeIn 0.3s ease-in-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hidden { display: none; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <div class="absolute top-6 right-8 flex items-center space-x-4 z-10">
        <span id="nav-text" onclick="toggleAuth()" class="text-sm font-medium text-gray-400 hover:text-white transition cursor-pointer">회원가입</span>
        <button onclick="toggleTheme()" class="text-gray-400 hover:text-white transition">
            <i id="theme-icon" class="fa-solid fa-moon text-lg"></i>
        </button>
    </div>

    <div class="w-full max-w-md glass-card p-10 rounded-[24px] fade-in relative overflow-hidden">
        
        <div id="login-section" class="space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">로그인 👋</h1>
                <p class="text-gray-400 text-sm">서비스를 이용하려면 계정에 로그인하세요.</p>
            </div>

            <div class="space-y-3">
                <button class="w-full btn-discord text-white font-bold py-3.5 rounded-xl flex items-center justify-center space-x-3 active:scale-[0.98]">
                    <i class="fa-brands fa-discord text-xl"></i>
                    <span>디스코드로 로그인</span>
                </button>
                <div class="relative flex items-center justify-center">
                    <div class="absolute inset-0 flex items-center">
                        <div class="w-full border-t border-gray-800"></div>
                    </div>
                    <span class="relative px-3 text-xs text-gray-600 bg-transparent">또는</span>
                </div>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">아이디</label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호</label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm pr-12">
                    <button type="button" class="absolute right-4 top-[40px] text-gray-500 hover:text-white">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:opacity-90 transition-all mt-3">
                    로그인 하기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    아직 계정이 없으신가요? 
                    <button onclick="toggleAuth()" class="font-bold hover:underline ml-1">회원가입</button>
                </p>
            </div>
        </div>

        <div id="signup-section" class="hidden space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">회원가입 👋</h1>
                <p class="text-gray-400 text-sm">정보를 입력하여 새 계정을 생성하세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2 ml-1">아이디 <span class="text-red-500">*</span></label>
                    <input type="text" placeholder="사용할 아이디 입력" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 설정" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2 ml-1">비밀번호 확인 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 재입력" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:opacity-90 transition-all mt-3">
                    계정 만들기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    이미 계정이 있으신가요? 
                    <button onclick="toggleAuth()" class="font-bold hover:underline ml-1">로그인</button>
                </p>
            </div>
        </div>

    </div>

    <script>
        let isLoginView = true;

        // 화면 전환 함수
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

        // 테마 전환 함수 (배경 검정 <-> 흰색)
        function toggleTheme() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            
            body.classList.toggle('light-mode');

            if (body.classList.contains('light-mode')) {
                icon.classList.replace('fa-moon', 'fa-sun'); // 달 -> 태양
            } else {
                icon.classList.replace('fa-sun', 'fa-moon'); // 태양 -> 달
            }
        }
    </script>
</body>
</html>
