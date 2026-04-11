<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>세일러 피스 - 로그인</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: #000; /* 완전한 검정 배경 */
            color: #fff; 
            overflow: hidden; /* 스크롤 방지 */
        }

        /* [유리 박스 핵심 스타일] - 이미지 디자인 유지하며 투명도 조절 */
        .glass-card {
            background: rgba(255, 255, 255, 0.03); /* 아주 미세한 흰색 투명 */
            backdrop-filter: blur(10px); /* 은은한 흐림 효과 */
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05); /* 아주 얇은 테두리 */
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.7);
        }

        /* 입력창 스타일 - 이미지와 동일하게 */
        .input-field {
            background-color: #1a1a1a; /* 짙은 회색 */
            border: 1px solid #333;
            border-radius: 12px;
            transition: all 0.2s ease;
        }
        .input-field:focus {
            border-color: #555;
            outline: none;
            background-color: #222;
        }

        /* 디스코드 버튼 전용 색상 */
        .btn-discord {
            background-color: #5865F2;
            transition: background-color 0.2s;
        }
        .btn-discord:hover {
            background-color: #4752C4;
        }

        /* 화면 전환 애니메이션 */
        .fade-in { animation: fadeIn 0.3s ease-in-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hidden { display: none; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <div onclick="toggleAuth()" class="absolute top-6 right-8 flex items-center space-x-4 cursor-pointer group z-10">
        <span id="nav-text" class="text-sm font-medium text-gray-400 group-hover:text-white transition">회원가입</span>
        <button class="text-gray-400 group-hover:text-white transition">
            <i class="fa-solid fa-moon text-lg"></i>
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
                    <button type="button" class="absolute right-4 top-[40px] text-gray-500 hover:text-white transition">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:bg-gray-200 transition-all mt-3">
                    로그인 하기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    아직 계정이 없으신가요? 
                    <button onclick="toggleAuth()" class="text-white font-bold hover:underline ml-1">회원가입</button>
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
                    <input type="password" placeholder="비밀번호 재입력" class="input-field w-full px-4 py-3.5 text-sm pr-12">
                    <button type="button" class="absolute right-4 top-[40px] text-gray-500 hover:text-white transition">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:bg-gray-200 transition-all mt-3">
                    계정 만들기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    이미 계정이 있으신가요? 
                    <button onclick="toggleAuth()" class="text-white font-bold hover:underline ml-1">로그인</button>
                </p>
            </div>
        </div>

    </div>

    <script>
        let isLoginView = true;

        // 로그인/회원가입 화면 전환 함수
        function toggleAuth() {
            const loginSec = document.getElementById('login-section');
            const signupSec = document.getElementById('signup-section');
            const navText = document.getElementById('nav-text');

            if (isLoginView) {
                // 회원가입 화면으로 전환
                loginSec.classList.add('hidden');
                signupSec.classList.remove('hidden');
                navText.innerText = '로그인';
            } else {
                // 로그인 화면으로 전환
                signupSec.classList.add('hidden');
                loginSec.classList.remove('hidden');
                navText.innerText = '회원가입';
            }
            isLoginView = !isLoginView;
        }
    </script>
</body>
</html>
