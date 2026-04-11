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

        .product-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }

        /* 하단 수치 박스 */
        .bottom-stats-box {
            display: flex;
            justify-content: space-around;
            padding: 6px 0;
            margin-top: 8px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.02);
        }
        .stat-unit { text-align: center; }
        .stat-title { font-size: 8px; color: #666; display: block; }
        .stat-num { font-size: 9px; font-weight: 700; color: #bbb; }

        /* 구매 영역: 버튼 + 재고 */
        .action-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
        .stock-tag {
            flex-shrink: 0;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
            font-size: 10px;
            color: #888;
            text-align: center;
            min-width: 55px;
        }

        .hr-line { height: 1px; background: rgba(255, 255, 255, 0.08); margin: 20px 0; border: none; }

        /* 이용약관 텍스트 */
        .terms-box {
            padding: 20px;
            font-size: 11px;
            line-height: 1.6;
            color: #555;
            border-radius: 16px;
            margin-top: 20px;
            background: rgba(255, 255, 255, 0.01);
        }

        @media (max-width: 640px) {
            .product-card { padding: 12px !important; border-radius: 20px !important; }
            .product-name { font-size: 14px !important; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="flex items-center space-x-2">
            <button class="px-3 py-2 rounded-lg bg-white text-black font-bold text-xs">충전하기</button>
            <button class="px-3 py-2 rounded-lg glass-card text-white font-bold text-xs">내 정보</button>
            <button onclick="toggleTheme()" class="p-2 text-gray-500"><i id="t-icon" class="fa-solid fa-moon text-sm"></i></button>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto p-4">
        <div class="py-4">
            <h1 class="text-2xl font-bold mb-1">구매하기</h1>
            <p class="text-gray-500 text-xs">아래 제품을 선택하여 구매하세요.</p>
        </div>

        <hr class="hr-line">

        <div class="product-grid">
            <div class="glass-card product-card p-5 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-robot text-3xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-base font-bold truncate">자판기 봇</h3>
                <div class="text-sm font-medium text-gray-400 mt-1 mb-3">30,000₩</div>

                <div class="mt-auto">
                    <div class="action-row">
                        <button class="flex-1 bg-white text-black py-2 rounded-lg font-bold text-xs">구매</button>
                        <div class="stock-tag">재고 12개</div>
                    </div>
                    
                    <div class="bottom-stats-box">
                        <div class="stat-unit"><span class="stat-title">평점</span><span class="stat-num">4.9</span></div>
                        <div class="stat-unit"><span class="stat-title">만족도</span><span class="stat-num">99%</span></div>
                        <div class="stat-unit"><span class="stat-title">지급</span><span class="stat-num">즉시</span></div>
                    </div>
                </div>
            </div>

            <div class="glass-card product-card p-5 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-bolt text-3xl text-gray-600"></i>
                </div>
                
                <h3 class="product-name text-base font-bold truncate">매크로</h3>
                <div class="text-sm font-medium text-gray-400 mt-1 mb-3">10,000₩</div>

                <div class="mt-auto">
                    <div class="action-row">
                        <button class="flex-1 bg-white text-black py-2 rounded-lg font-bold text-xs">구매</button>
                        <div class="stock-tag">재고 5개</div>
                    </div>
                    
                    <div class="bottom-stats-box">
                        <div class="stat-unit"><span class="stat-title">평점</span><span class="stat-num">4.7</span></div>
                        <div class="stat-unit"><span class="stat-title">만족도</span><span class="stat-num">97%</span></div>
                        <div class="stat-unit"><span class="stat-title">지급</span><span class="stat-num">1분</span></div>
                    </div>
                </div>
            </div>
        </div>

        <hr class="hr-line">

        <div class="terms-box glass-card">
            <h4 class="font-bold mb-2 text-gray-400">이용약관 및 주의사항</h4>
            <p>1. 모든 제품은 구매 즉시 지급 시스템을 통해 전달됩니다.<br>
            2. 디지털 상품 특성상 수령 후 단순 변심으로 인한 환불은 불가능합니다.<br>
            3. 제품 결함 발생 시 고객센터를 통해 24시간 이내에 문의해 주시기 바랍니다.<br>
            4. 타인에게 계정을 공유하거나 프로그램을 불법 수정할 경우 이용이 제한될 수 있습니다.</p>
        </div>
    </main>

    <script>
        function toggleTheme() {
            const b = document.body; const i = document.getElementById('t-icon');
            b.classList.toggle('light-mode');
            const isL = b.classList.contains('light-mode');
            i.className = isL ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
        }
    </script>
</body>
</html>
