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
        
        /* 네비게이션 바: 로고 제거 및 버튼 정렬 */
        nav {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: flex-end; /* 오른쪽으로 정렬 */
            padding: 1.25rem 2rem;
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

        /* 제품 카드 스타일 및 2열 배치 */
        .product-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr); /* 2칸 고정 */
            gap: 2rem;
        }

        /* 구분선 스타일 (로그인 페이지와 동일) */
        .section-separator {
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            margin: 2.5rem 0;
        }
        body.light-mode .section-separator {
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
        }

        .btn-action {
            padding: 10px 20px;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
        }
        .btn-action:active { transform: scale(0.97); }

        .product-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.05);
        }
    </style>
</head>
<body>

    <nav class="sticky top-0 z-50">
        <div class="flex items-center space-x-3">
            <button onclick="alert('충전 페이지로 이동')" class="btn-action bg-white text-black hover:opacity-90">
                <i class="fa-solid fa-bolt mr-2"></i>충전하기
            </button>
            <button onclick="alert('내 정보 확인')" class="btn-action glass-card text-white">
                <i class="fa-solid fa-user mr-2"></i>내 정보
            </button>
            <button onclick="toggleTheme()" class="ml-2 p-2 text-gray-400 hover:text-white">
                <i id="theme-icon" class="fa-solid fa-moon text-xl"></i>
            </button>
        </div>
    </nav>

    <main class="max-w-5xl mx-auto p-8 pt-12">
        <header class="mb-10">
            <h1 class="text-4xl font-bold mb-3 tracking-tight">Store</h1>
            <p class="text-gray-400 text-lg">성원님을 위한 프리미엄 서비스를 이용해 보세요.</p>
        </header>

        <div class="section-separator"></div>

        <div class="product-grid">
            
            <div class="glass-card product-card p-8 rounded-[28px] flex flex-col justify-between">
                <div>
                    <div class="w-full h-48 bg-white/5 rounded-2xl flex items-center justify-center mb-6">
                        <i class="fa-solid fa-robot text-5xl text-gray-600"></i>
                    </div>
                    <h3 class="text-2xl font-bold mb-2">디스코드 자판기 봇</h3>
                    <p class="text-gray-400 leading-relaxed">로블록스 아이템 자동 판매 및 기프팅 시스템이 통합된 고성능 봇입니다.</p>
                </div>
                <div class="flex justify-between items-center mt-8 pt-6 border-t border-white/5">
                    <span class="text-2xl font-bold">30,000₩</span>
                    <button class="bg-white text-black px-6 py-3 rounded-xl font-bold hover:opacity-90 transition">구매하기</button>
                </div>
            </div>

            <div class="glass-card product-card p-8 rounded-[28px] flex flex-col justify-between">
                <div>
                    <div class="w-full h-48 bg-white/5 rounded-2xl flex items-center justify-center mb-6">
                        <i class="fa-solid fa-code text-5xl text-gray-600"></i>
                    </div>
                    <h3 class="text-2xl font-bold mb-2">카카오톡 매크로</h3>
                    <p class="text-gray-400 leading-relaxed">다크 모드 UI와 백그라운드 실행을 지원하는 커스텀 매크로 프로그램입니다.</p>
                </div>
                <div class="flex justify-between items-center mt-8 pt-6 border-t border-white/5">
                    <span class="text-2xl font-bold">10,000₩</span>
                    <button class="bg-white text-black px-6 py-3 rounded-xl font-bold hover:opacity-90 transition">구매하기</button>
                </div>
            </div>

        </div>

        <div class="section-separator"></div>
    </main>

    <script>
        function toggleTheme() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            body.classList.toggle('light-mode');
            if (body.classList.contains('light-mode')) {
                icon.classList.replace('fa-moon', 'fa-sun');
                // 라이트 모드 시 내 정보 버튼 텍스트 색상 대응
                document.querySelector('.glass-card.text-white').classList.add('text-black');
                document.querySelector('.glass-card.text-white').classList.remove('text-white');
            } else {
                icon.classList.replace('fa-sun', 'fa-moon');
                document.querySelector('.glass-card.text-black').classList.add('text-white');
                document.querySelector('.glass-card.text-black').classList.remove('text-black');
            }
        }
    </script>
</body>
</html>
