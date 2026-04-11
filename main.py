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

        /* 모바일/PC 모두 강제 2열 배치 */
        .product-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px; /* 간격을 좁혀서 컴팩트하게 배치 */
        }

        /* 수치 데이터 가로 배열 */
        .stats-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin: 10px 0;
        }

        .stat-box { text-align: center; flex: 1; }
        .stat-label { font-size: 10px; color: #666; margin-bottom: 2px; display: block; }
        .stat-val { font-size: 11px; font-weight: 700; }

        /* 구분선 스타일 */
        .hr-line {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 20px 0;
            border: none;
        }
        body.light-mode .hr-line { background: rgba(0, 0, 0, 0.08); }

        .btn-top { padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 600; }
        
        /* 모바일 텍스트 크기 최적화 */
        @media (max-width: 640px) {
            .product-card { padding: 12px !important; border-radius: 20px !important; }
            .product-name { font-size: 14px !important; }
            .product-price { font-size: 16px !important; }
            .product-desc { display: none; } /* 모바일에서 설명 생략하여 공간 확보 */
            .buy-btn { padding: 6px 0 !important; font-size: 12px !important; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="flex items-center space-x-2">
            <button onclick="alert('충전')" class="btn-top bg-white text-black">충전하기</button>
            <button onclick="alert('정보')" class="btn-top glass-card text-white">내 정보</button>
            <button onclick="toggleTheme()" class="p-2 text-gray-500"><i id="t-icon" class="fa-solid fa-moon"></i></button>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto p-4">
        <div class="py-6">
            <h1 class="text-3xl font-bold mb-1">구매하기</h1>
            <p class="text-gray-500 text-sm">아래 제품을 선택하여 구매하세요.</p>
        </div>

        <hr class="hr-line">

        <div class="product-grid">
            
            <div class="glass-card product-card p-5 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-robot text-3xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-lg font-bold truncate">자판기 봇</h3>
                <p class="product-desc text-xs text-gray-500 mt-1">자동 판매 시스템</p>

                <div class="stats-row">
                    <div class="stat-box">
                        <span class="stat-label">평점</span>
                        <span class="stat-val">4.9</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">만족</span>
                        <span class="stat-val">99%</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">지급</span>
                        <span class="stat-val">즉시</span>
                    </div>
                </div>

                <div class="mt-auto">
                    <div class="product-price text-lg font-bold mb-2">30,000₩</div>
                    <button class="buy-btn w-full bg-white text-black py-2 rounded-lg font-bold text-sm">구매</button>
                </div>
            </div>

            <div class="glass-card product-card p-5 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-bolt text-3xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-lg font-bold truncate">매크로</h3>
                <p class="product-desc text-xs text-gray-500 mt-1">고성능 자동화</p>

                <div class="stats-row">
                    <div class="stat-box">
                        <span class="stat-label">평점</span>
                        <span class="stat-val">4.7</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">만족</span>
                        <span class="stat-val">97%</span>
                    </div>
                    <div class="stat-box">
                        <span class="stat-label">지급</span>
                        <span class="stat-val">1분</span>
                    </div>
                </div>

                <div class="mt-auto">
                    <div class="product-price text-lg font-bold mb-2">10,000₩</div>
                    <button class="buy-btn w-full bg-white text-black py-2 rounded-lg font-bold text-sm">구매</button>
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
