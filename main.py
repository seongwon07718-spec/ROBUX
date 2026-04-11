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
            /* 은은한 배경 그라데이션 */
            background: radial-gradient(circle at top right, #1a1a1a, #000); 
            color: #fff; 
            overflow: hidden; 
        }

        /* [유리 박스 핵심 스타일] */
        .glass-card {
            background: rgba(255, 255, 255, 0.03); /* 매우 투명한 흰색 */
            backdrop-filter: blur(15px); /* 배경 흐림 효과 */
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1); /* 미세한 테두리 */
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }

        .input-field {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            transition: all 0.2s ease;
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

    <div onclick="toggleAuth()" class="absolute top-8 right-8 flex items-center space-x-3 cursor-pointer group z-10">
        <span id="nav-text" class="text-sm font-medium text-gray-400 group-hover:text-white transition-colors">회원가입</span>
        <div class="p-2 rounded-full bg-white/5 group-hover:bg-white/10 transition-colors">
            <i id="nav-icon" class="fa-solid fa-moon text-lg text-gray-400 group-hover:text-white"></i>
        </div>
    </div>

    <div class="w-full max-w-md glass-card p-8 md:p-10 rounded-[32px] fade-in relative overflow-hidden">
        
        <div class="absolute -top-24 -left-24 w-48 h-48 bg-white/5 rounded-full blur-3xl"></div>

        <div id="login-section" class="space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">로그인 👋</h1>
                <p class="text-gray-400 text-sm leading-relaxed">세일러 피스 서비스에 오신 것을 환영합니다.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">아이디</label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">비밀번호</label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-4 text-sm pr-12">
                    <button type="button" class="absolute right-4 top-11 text-gray-500 hover:text-white transition">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-2xl hover:bg-gray-200 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 mt-4 shadow-lg shadow-white/5">
                    로그인 하기
                </button>
            </form>

            <div class="pt-6 text-center">
                <p class="text-sm text-gray-500">
                    아직 계정이 없으신가요? 
                    <button onclick="toggleAuth()" class="text-white font-bold hover:underline ml-1">회원가입</button>
                </p>
            </div>
        </div>

        <div id="signup-section" class="hidden space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">회원가입 👋</h1>
                <p class="text-gray-400 text-sm leading-relaxed">정보를 입력하여 새 계정을 생성하세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">아이디 <span class="text-red-500">*</span></label>
                    <input type="text" placeholder="사용할 아이디 입력" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">비밀번호 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 설정" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">비밀번호 확인 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호 재입력" class="input-field w-full px-4 py-4 text-sm">
                </div>
                <button class="w-full bg-white text-black font-bold py-4 rounded-2xl hover:bg-gray-200 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 mt-4 shadow-lg shadow-white/5">
                    계정 만들기
                </button>
            </form>

            <div class="pt-6 text-center">
                <p class="text-sm text-gray-500">
                    이미 계정이 있으신가요? 
                    <button onclick="toggleAuth()" class="text-white font-bold hover:underline ml-1">로그인</button>
                </p>
            </div>
        </div>
    </div>

    <script>
        let isLoginView = true;

        function toggleAuth() {
            const loginSec = document.getElementById('login-section');
            const signupSec = document.getElementById('signup-section');
            const navText = document.getElementById('nav-text');
            const navIcon = document.getElementById('nav-icon');

            if (isLoginView) {
                loginSec.classList.add('hidden');
                signupSec.classList.remove('hidden');
                navText.innerText = '로그인하러 가기';
                navIcon.className = 'fa-solid fa-arrow-right-to-bracket text-lg';
            } else {
                signupSec.classList.add('hidden');
                loginSec.classList.remove('hidden');
                navText.innerText = '회원가입';
                navIcon.className = 'fa-solid fa-moon text-lg';
            }
            isLoginView = !isLoginView;
        }
    </script>
</body>
</html>
