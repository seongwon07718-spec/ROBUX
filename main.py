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
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; overflow-x: hidden; }
        .input-field {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            transition: all 0.3s ease;
        }
        .input-field:focus {
            border-color: #666;
            outline: none;
            background-color: #222;
        }
        .hidden { display: none; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">

    <div class="absolute top-6 right-8 flex items-center space-x-4">
        <span id="nav-text" class="text-sm font-medium text-gray-400">로그인</span>
        <button class="text-gray-400 hover:text-white transition">
            <i class="fa-solid fa-moon text-lg"></i>
        </button>
    </div>

    <div class="w-full max-w-md space-y-8">
        
        <div id="login-section" class="space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">로그인 👋</h1>
                <p class="text-gray-400 text-sm">서비스를 이용하려면 계정에 로그인하세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2">아이디</label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2">비밀번호</label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm pr-10">
                    <button type="button" class="absolute right-3 top-10 text-gray-500 hover:text-gray-300">
                        <i class="fa-regular fa-eye text-lg"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:bg-gray-200 transition-all mt-2">
                    로그인 하기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    아직 계정이 없으신가요? 
                    <button onclick="toggleForm('signup')" class="text-white font-bold hover:underline ml-1 cursor-pointer">회원가입</button>
                </p>
            </div>
        </div>

        <div id="signup-section" class="hidden space-y-8">
            <div class="text-left">
                <h1 class="text-3xl font-bold mb-2">회원가입 👋</h1>
                <p class="text-gray-400 text-sm">아이디와 비밀번호를 입력해 계정을 만들어주세요.</p>
            </div>

            <form class="space-y-5" onsubmit="return false;">
                <div>
                    <label class="block text-sm font-medium mb-2">아이디 <span class="text-red-500">*</span></label>
                    <input type="text" placeholder="아이디를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm">
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2">비밀번호 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호를 입력하세요" class="input-field w-full px-4 py-3.5 text-sm pr-10">
                    <button type="button" class="absolute right-3 top-10 text-gray-500 hover:text-gray-300">
                        <i class="fa-regular fa-eye text-lg"></i>
                    </button>
                </div>
                <div class="relative">
                    <label class="block text-sm font-medium mb-2">비밀번호 확인 <span class="text-red-500">*</span></label>
                    <input type="password" placeholder="비밀번호를 확인해주세요" class="input-field w-full px-4 py-3.5 text-sm pr-10">
                    <button type="button" class="absolute right-3 top-10 text-gray-500 hover:text-gray-300">
                        <i class="fa-regular fa-eye text-lg"></i>
                    </button>
                </div>
                <button class="w-full bg-white text-black font-bold py-3.5 rounded-xl hover:bg-gray-200 transition-all mt-2">
                    계정 만들기
                </button>
            </form>

            <div class="pt-6 border-t border-gray-800 text-center">
                <p class="text-sm text-gray-400">
                    이미 계정이 있으신가요? 
                    <button onclick="toggleForm('login')" class="text-white font-bold hover:underline ml-1 cursor-pointer">로그인</button>
                </p>
            </div>
        </div>

    </div>

    <script>
        function toggleForm(type) {
            const loginSec = document.getElementById('login-section');
            const signupSec = document.getElementById('signup-section');
            const navText = document.getElementById('nav-text');

            if (type === 'signup') {
                loginSec.classList.add('hidden');
                signupSec.classList.remove('hidden');
                navText.innerText = '회원가입';
            } else {
                signupSec.classList.add('hidden');
                loginSec.classList.remove('hidden');
                navText.innerText = '로그인';
            }
        }
    </script>
</body>
</html>
