<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>세일러 피스 - 상점</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; transition: background-color 0.3s; margin: 0; }
        body.light-mode { background-color: #ffffff; color: #000; }
        
        /* 네비게이션 바 유리 효과 */
        nav {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        body.light-mode nav {
            background: rgba(0, 0, 0, 0.03);
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s;
        }
        body.light-mode .glass-card {
            background: rgba(0, 0, 0, 0.03);
            border: 1px solid rgba(0, 0, 0, 0.1);
        }

        .product-card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.2);
        }
        body.light-mode .product-card:hover {
            border-color: rgba(0, 0, 0, 0.2);
        }

        .btn-action {
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 600;
            transition: all 0.2s;
        }
    </style>
</head>
<body class="min-h-screen">

    <nav class="sticky top-0 z-50 px-8 py-4 flex justify-between items-center">
        <div class="text-xl font-bold tracking-tighter">SAILOR PIECE</div>
        
        <div class="flex items-center space-x-4">
            <button onclick="alert('충전 페이지로 이동')" class="btn-action bg-white text-black hover:opacity-80">
                <i class="fa-solid fa-bolt mr-2"></i>충전하기
            </button>
            <button onclick="alert('내 정보 확인')" class="btn-action glass-card text-white body.light-mode:text-black">
                <i class="fa-solid fa-user mr-2"></i>내 정보
            </button>
            <button onclick="toggleTheme()" class="text-gray-400 hover:text-white transition ml-2">
                <i id="theme-icon" class="fa-solid fa-moon text-lg"></i>
            </button>
        </div>
    </nav>

    <main class="max-w-6xl mx-auto p-10">
        <header class="mb-12">
            <h2 class="text-3xl font-bold mb-2">프리미엄 제품 👋</h2>
            <p class="text-gray-400">성원님이 선택하신 최상의 제품들을 확인하세요.</p>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            
            <div class="glass-card product-card p-6 rounded-[24px] space-y-4">
                <div class="w-full h-40 bg-white/5 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-box-open text-4xl text-gray-500"></i>
                </div>
                <div>
                    <h3 class="text-lg font-bold">로블록스 자동 선물 봇</h3>
                    <p class="text-sm text-gray-400 mt-1">Pet Simulator 99 전용 자동화 스크립트</p>
                </div>
                <div class="flex justify-between items-center pt-4">
                    <span class="text-xl font-bold">15,000원</span>
                    <button class="btn-action bg-white text-black py-2 px-5 rounded-lg font-bold">구매하기</button>
                </div>
            </div>

            <div class="glass-card product-card p-6 rounded-[24px] space-y-4">
                <div class="w-full h-40 bg-white/5 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-robot text-4xl text-gray-500"></i>
                </div>
                <div>
                    <h3 class="text-lg font-bold">디스코드 자판기 봇 V2</h3>
                    <p class="text-sm text-gray-400 mt-1">깔끔한 UI와 빠른 처리 속도</p>
                </div>
                <div class="flex justify-between items-center pt-4">
                    <span class="text-xl font-bold">30,000원</span>
                    <button class="btn-action bg-white text-black py-2 px-5 rounded-lg font-bold">구매하기</button>
                </div>
            </div>

        </div>
    </main>

    <script>
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
