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
            background-color: #000; /* 기본 배경 검정 */
            color: #fff; 
            transition: background-color 0.3s ease;
            overflow: hidden;
        }

        /* 배경 전환용 클래스 */
        body.alt-bg { background-color: #1a1a1a; }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }

        .input-field {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            transition: all 0.2s;
        }
        
        .input-field:focus {
            border-color: rgba(255, 255, 255, 0.3);
            background: rgba(255, 255, 255, 0.08);
            outline: none;
        }

        .fade-in { animation: fadeIn 0.4s ease-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.98); }
            to { opacity: 1; transform: scale(1); }
        }

        .hidden { display: none; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <div class="absolute top-8 right-8 flex items-center space-x-6 z-10">
        <button onclick="toggleAuth()" id="nav-text" class="text-sm font-semibold text-gray-400 hover:text-white transition-colors">
            회원가입
        </button>
        
        <button onclick="toggleBg()" class="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-all active:scale-90">
            <i id="theme-icon" class="fa-solid fa-moon text-lg text-gray-300"></i>
        </button>
    </div>

    <div class="w-full max-w-md glass-card p-10 rounded-[32px] fade-in relative">
        
        <div id="login-section" class="space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">로그인 👋</h1>
                <p class="text-gray-400 text-sm">세일러 피스 자동 판매봇에 오신 것을 환영합니다.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-tighter mb-2 ml-1">ID</label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-tighter mb-2 ml-1">Password</label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-4 text-sm pr-12">
                    <button type="button" class="absolute right-4 top-11 text-gray-500 hover:text-white">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-2xl hover:bg-gray-200 transition-all mt-4">
                    로그인
                </button>
            </form>

            <div class="pt-4 text-center">
                <button onclick="toggleAuth()" class="text-sm text-gray-500 hover:text-white transition">
                    아직 계정이 없으신가요? <span class="font-bold text-white underline underline-offset-4 ml-1">회원가입</span>
                </button>
            </div>
        </div>

        <div id="signup-section" class="hidden space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">회원가입 👋</h1>
                <p class="text-gray-400 text-sm">새로운 계정을 생성하여 시작하세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-tighter mb-2 ml-1">ID <span class="text-red-500">*</span></label>
                    <input type="text" placeholder="아이디 입력" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-tighter mb-2 ml-1">Password <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 설정" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-500 uppercase tracking-tighter mb-2 ml-1">Confirm Password <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 재입력" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-2xl hover:bg-gray-200 transition-all mt-4">
                    가입 완료
                </button>
            </form>

            <div class="pt-4 text-center">
                <button onclick="toggleAuth()" class="text-sm text-gray-500 hover:text-white transition">
                    이미 계정이 있으신가요? <span class="font-bold text-white underline underline-offset-4 ml-1">로그인</span>
                </button>
            </div>
        </div>
    </div>

    <script>
        let isLoginView = true;

        // 배경색 토글 함수
        function toggleBg() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            body.classList.toggle('alt-bg');
            
            if (body.classList.contains('alt-bg')) {
                icon.className = 'fa-solid fa-sun text-lg text-yellow-400';
            } else {
                icon.className = 'fa-solid fa-moon text-lg text-gray-300';
            }
        }

        // 로그인/회원가입 전환 함수
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
    </script>
</body>
</html>
