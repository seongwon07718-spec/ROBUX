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
        
        nav { background: rgba(255, 255, 255, 0.02); backdrop-filter: blur(15px); border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 0.8rem 1rem; display: flex; justify-content: flex-end; position: sticky; top: 0; z-index: 100; }
        .glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.06); }
        body.light-mode .glass-card { background: rgba(0, 0, 0, 0.02); border: 1px solid rgba(0, 0, 0, 0.08); }

        .product-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }

        /* 후기 애니메이션 */
        .review-container { height: 24px; overflow: hidden; position: relative; margin-top: 8px; }
        .review-track { position: absolute; width: 100%; animation: slideUp 8s infinite; }
        .review-item { height: 24px; font-size: 11px; color: #888; display: flex; align-items: center; gap: 6px; }
        @keyframes slideUp {
            0%, 20% { transform: translateY(0); }
            25%, 45% { transform: translateY(-24px); }
            50%, 70% { transform: translateY(-48px); }
            75%, 95% { transform: translateY(-72px); }
            100% { transform: translateY(0); }
        }

        /* 버튼 3:7 재고 비율 조정 */
        .action-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
        .buy-btn { width: 30%; background: #fff; color: #000; padding: 8px 0; border-radius: 10px; font-weight: 700; font-size: 11px; text-align: center; }
        .stock-tag { flex: 1; padding: 8px 0; border-radius: 10px; background: rgba(255, 255, 255, 0.05); font-size: 10px; color: #aaa; text-align: center; font-weight: 600; }

        .bottom-stats-box { display: flex; justify-content: space-around; padding: 6px 0; margin-top: 8px; border-radius: 10px; background: rgba(255, 255, 255, 0.02); }
        .stat-unit { text-align: center; }
        .stat-title { font-size: 8px; color: #666; display: block; }
        .stat-num { font-size: 9px; font-weight: 700; color: #bbb; }

        .hr-line { height: 1px; background: rgba(255, 255, 255, 0.08); margin: 16px 0; border: none; }
        .terms-box { padding: 18px; font-size: 10px; line-height: 1.6; color: #555; border-radius: 16px; margin-top: 20px; background: rgba(255, 255, 255, 0.01); }

        @media (max-width: 640px) {
            .product-card { padding: 12px !important; border-radius: 20px !important; }
            .product-name { font-size: 14px !important; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="flex items-center space-x-2">
            <button class="px-3 py-1.5 rounded-lg bg-white text-black font-bold text-[11px]">충전하기</button>
            <button class="px-3 py-1.5 rounded-lg glass-card text-white font-bold text-[11px]">내 정보</button>
            <button onclick="toggleTheme()" class="p-2 text-gray-500"><i id="t-icon" class="fa-solid fa-moon text-sm"></i></button>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto p-4">
        <div class="py-2">
            <h1 class="text-2xl font-bold mb-1">구매하기</h1>
            <p class="text-gray-500 text-xs">아래 제품을 선택하여 구매하세요.</p>
            
            <div class="review-container">
                <div class="review-track">
                    <div class="review-item"><i class="fa-solid fa-circle-check text-green-500"></i> user***님이 자판기 봇을 구매했습니다.</div>
                    <div class="review-item"><i class="fa-solid fa-comment-dots text-blue-400"></i> "지급 진짜 빠르네요 만족합니다!"</div>
                    <div class="review-item"><i class="fa-solid fa-circle-check text-green-500"></i> kimm***님이 매크로를 구매했습니다.</div>
                    <div class="review-item"><i class="fa-solid fa-comment-dots text-blue-400"></i> "디자인이 너무 예뻐요."</div>
                </div>
            </div>
        </div>

        <hr class="hr-line">

        <div class="product-grid">
            <div class="glass-card product-card p-4 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-robot text-3xl text-gray-600"></i>
                </div>
                <h3 class="product-name text-sm font-bold truncate">자판기 봇</h3>
                <div class="text-xs font-medium text-gray-400 mt-1 mb-3">30,000₩</div>

                <div class="mt-auto">
                    <div class="action-row">
                        <button class="buy-btn">구매</button>
                        <div class="stock-tag">재고 12개</div>
                    </div>
                    <div class="bottom-stats-box">
                        <div class="stat-unit"><span class="stat-title">평점</span><span class="stat-num">4.9</span></div>
                        <div class="stat-unit"><span class="stat-title">만족도</span><span class="stat-num">99%</span></div>
                        <div class="stat-unit"><span class="stat-title">지급</span><span class="stat-num">즉시</span></div>
                    </div>
                </div>
            </div>

            <div class="glass-card product-card p-4 rounded-[24px] flex flex-col">
                <div class="w-full aspect-square bg-white/5 rounded-xl flex items-center justify-center mb-3">
                    <i class="fa-solid fa-bolt text-3xl text-gray-600"></i>
                </div>
                <h3 class="product-name text-sm font-bold truncate">매크로</h3>
                <div class="text-xs font-medium text-gray-400 mt-1 mb-3">10,000₩</div>

                <div class="mt-auto">
                    <div class="action-row">
                        <button class="buy-btn">구매</button>
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
            <h4 class="font-bold mb-1 text-gray-400">주의사항</h4>
            <p>모든 상품은 디지털 재화이며 발송 후 환불이 불가합니다.</p>
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
