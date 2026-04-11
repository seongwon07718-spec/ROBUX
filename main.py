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
        
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; transition: background-color 0.3s; margin: 0; min-height: 100vh; }
        body.light-mode { background-color: #ffffff; color: #000; }
        
        /* 네비게이션 바: 모바일 대응 */
        nav {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding: 1rem 1.5rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        body.light-mode .glass-card { background: rgba(0, 0, 0, 0.02); border: 1px solid rgba(0, 0, 0, 0.08); }

        /* 제품 그리드: PC 2열, 모바일 1열 자동 전환 */
        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        /* 상세 수치 가로 정렬 레이아웃 */
        .stats-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin: 1.5rem 0;
        }
        body.light-mode .stats-container { border-color: rgba(0, 0, 0, 0.05); }

        .stat-item { text-align: center; flex: 1; }
        .stat-label { font-size: 0.7rem; color: #888; margin-bottom: 4px; display: block; }
        .stat-value { font-size: 0.9rem; font-weight: 700; color: #fff; }
        body.light-mode .stat-value { color: #000; }

        .btn-action {
            padding: 10px 18px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            transition: 0.2s;
        }

        .product-card:hover { transform: translateY(-8px); background: rgba(255, 255, 255, 0.06); }
        
        /* 모바일 최적화 여백 */
        @media (max-width: 640px) {
            .product-grid { grid-template-columns: 1fr; }
            main { padding: 1.5rem; }
            .text-4xl { font-size: 2rem; }
        }
    </style>
</head>
<body>

    <nav class="flex justify-end items-center space-x-3">
        <button onclick="alert('충전하기')" class="btn-action bg-white text-black">
            <i class="fa-solid fa-bolt mr-1.5"></i>충전
        </button>
        <button onclick="alert('내 정보')" class="btn-action glass-card text-white">
            <i class="fa-solid fa-user mr-1.5"></i>내 정보
        </button>
        <button onclick="toggleTheme()" class="p-2 text-gray-400">
            <i id="theme-icon" class="fa-solid fa-moon text-lg"></i>
        </button>
    </nav>

    <main class="max-w-6xl mx-auto px-6 py-12">
        <header class="mb-10 text-center md:text-left">
            <h1 class="text-4xl font-bold tracking-tight mb-3">Store</h1>
            <p class="text-gray-400">프리미엄 제품 라인업을 확인하세요.</p>
        </header>

        <div class="product-grid">
            
            <div class="glass-card product-card p-7 rounded-[30px] flex flex-col">
                <div class="w-full h-44 bg-white/5 rounded-2xl flex items-center justify-center mb-5">
                    <i class="fa-solid fa-robot text-5xl text-gray-500"></i>
                </div>
                
                <h3 class="text-xl font-bold">디스코드 자판기 봇</h3>
                <p class="text-sm text-gray-400 mt-2 h-10 overflow-hidden">로블록스 자동 선물 및 판매 통합 시스템</p>

                <div class="stats-container">
                    <div class="stat-item border-r border-white/5">
                        <span class="stat-label">만족도</span>
                        <span class="stat-value">99%</span>
                    </div>
                    <div class="stat-item border-r border-white/5">
                        <span class="stat-label">평점</span>
                        <span class="stat-value">4.9/5</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">지급속도</span>
                        <span class="stat-value">즉시</span>
                    </div>
                </div>

                <div class="flex justify-between items-center mt-auto">
                    <span class="text-2xl font-bold">30,000₩</span>
                    <button class="bg-white text-black px-6 py-2.5 rounded-xl font-bold text-sm">구매하기</button>
                </div>
            </div>

            <div class="glass-card product-card p-7 rounded-[30px] flex flex-col">
                <div class="w-full h-44 bg-white/5 rounded-2xl flex items-center justify-center mb-5">
                    <i class="fa-solid fa-bolt-lightning text-5xl text-gray-500"></i>
                </div>
                
                <h3 class="text-xl font-bold">카카오톡 매크로</h3>
                <p class="text-sm text-gray-400 mt-2 h-10 overflow-hidden">다크모드 지원 고성능 백그라운드 매크로</p>

                <div class="stats-container">
                    <div class="stat-item border-r border-white/5">
                        <span class="stat-label">만족도</span>
                        <span class="stat-value">97%</span>
                    </div>
                    <div class="stat-item border-r border-white/5">
                        <span class="stat-label">평점</span>
                        <span class="stat-value">4.7/5</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">지급속도</span>
                        <span class="stat-value">1분내</span>
                    </div>
                </div>

                <div class="flex justify-between items-center mt-auto">
                    <span class="text-2xl font-bold">10,000₩</span>
                    <button class="bg-white text-black px-6 py-2.5 rounded-xl font-bold text-sm">구매하기</button>
                </div>
            </div>

        </div>
    </main>

    <script>
        function toggleTheme() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            body.classList.toggle('light-mode');
            
            const isLight = body.classList.contains('light-mode');
            icon.classList.replace(isLight ? 'fa-moon' : 'fa-sun', isLight ? 'fa-sun' : 'fa-moon');
            
            const userInfoBtn = document.querySelector('.glass-card.text-white, .glass-card.text-black');
            if (isLight) {
                userInfoBtn.classList.replace('text-white', 'text-black');
            } else {
                userInfoBtn.classList.replace('text-black', 'text-white');
            }
        }
    </script>
</body>
</html>
