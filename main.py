<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>세일러 피스</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; margin: 0; min-height: 100vh; -webkit-font-smoothing: antialiased; }
        body.light-mode { background-color: #fff; color: #000; }
        
        nav {
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding: 0.8rem 1rem;
            display: flex;
            justify-content: flex-end;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        body.light-mode .glass-card { background: rgba(0, 0, 0, 0.02); border: 1px solid rgba(0, 0, 0, 0.08); }

        /* 제품 그리드 2열 고정 */
        .product-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        /* 하단 수치용 전용 유리 박스 */
        .bottom-stats-box {
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 8px 4px;
            margin-top: 10px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .stat-unit { text-align: center; }
        .stat-title { font-size: 9px; color: #777; display: block; margin-bottom: 1px; }
        .stat-num { font-size: 10px; font-weight: 700; color: #ddd; }
        body.light-mode .stat-num { color: #333; }

        .hr-line {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 20px 0;
            border: none;
        }
        body.light-mode .hr-line { background: rgba(0, 0, 0, 0.08); }

        @media (max-width: 640px) {
            .product-card { padding: 14px !important; border-radius: 22px !important; }
            .product-name { font-size: 15px !important; }
            .product-desc { display: none; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="flex items-center space-x-2">
            <button onclick="alert('충전')" class="px-4 py-2 rounded-xl bg-white text-black font-bold text-sm">충전하기</button>
            <button onclick="alert('정보')" class="px-4 py-2 rounded-xl glass-card text-white font-bold text-sm">내 정보</button>
            <button onclick="toggleTheme()" class="p-2 text-gray-500"><i id="t-icon" class="fa-solid fa-moon"></i></button>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto p-5">
        <div class="py-4">
            <h1 class="text-3xl font-bold mb-1">구매하기</h1>
            <p class="text-gray-500 text-sm">아래 제품을 선택하여 구매하세요.</p>
        </div>

        <hr class="hr-line">

        <div class="product-grid">
            
            <div class="glass-card product-card p-6 rounded-[28px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-2xl flex items-center justify-center mb-4">
                    <i class="fa-solid fa-robot text-4xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-lg font-bold truncate">자판기 봇</h3>
                <p class="product-desc text-xs text-gray-500 mt-1 mb-3">자동 판매 시스템</p>

                <div class="mt-auto">
                    <div class="text-xl font-bold mb-3">30,000₩</div>
                    <button class="w-full bg-white text-black py-2.5 rounded-xl font-bold text-sm mb-1">구매</button>
                    
                    <div class="bottom-stats-box">
                        <div class="stat-unit">
                            <span class="stat-title">평점</span>
                            <span class="stat-num">4.9</span>
                        </div>
                        <div class="stat-unit">
                            <span class="stat-title">만족도</span>
                            <span class="stat-num">99%</span>
                        </div>
                        <div class="stat-unit">
                            <span class="stat-title">지급</span>
                            <span class="stat-num">즉시</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="glass-card product-card p-6 rounded-[28px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-2xl flex items-center justify-center mb-4">
                    <i class="fa-solid fa-bolt text-4xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-lg font-bold truncate">매크로</h3>
                <p class="product-desc text-xs text-gray-500 mt-1 mb-3">고성능 자동화</p>

                <div class="mt-auto">
                    <div class="text-xl font-bold mb-3">10,000₩</div>
                    <button class="w-full bg-white text-black py-2.5 rounded-xl font-bold text-sm mb-1">구매</button>
                    
                    <div class="bottom-stats-box">
                        <div class="stat-unit">
                            <span class="stat-title">평점</span>
                            <span class="stat-num">4.7</span>
                        </div>
                        <div class="stat-unit">
                            <span class="stat-title">만족도</span>
                            <span class="stat-num">97%</span>
                        </div>
                        <div class="stat-unit">
                            <span class="stat-title">지급</span>
                            <span class="stat-num">1분</span>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <hr class="hr-line">
    </main>

    <script>
        function toggleTheme() {
            const b = document.body;
            const i = document.getElementById('t-icon');
            b.classList.toggle('light-mode');
            const isL = b.classList.contains('light-mode');
            i.className = isL ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
            
            const btn = document.querySelector('.glass-card.text-white, .glass-card.text-black');
            if (isL) { btn.classList.replace('text-white', 'text-black'); }
            else { btn.classList.replace('text-black', 'text-white'); }
        }
    </script>
</body>
</html>
