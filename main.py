<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>포인트 충전 - 세일러 피스</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.06); }
        input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
</head>
<body>
    <div class="max-w-md w-full p-6">
        <div class="glass-card p-8 rounded-[32px]">
            <div class="text-center mb-8">
                <h2 class="text-2xl font-bold mb-2">포인트 충전</h2>
                <p class="text-gray-500 text-sm">입금 정보를 입력해 주세요.</p>
            </div>

            <form action="/change/api" method="POST" class="space-y-5">
                <div>
                    <label class="text-[10px] text-gray-500 ml-2 mb-1 block uppercase font-bold tracking-wider">Depositor</label>
                    <input type="text" name="depositor" placeholder="입금자명" required
                        class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-white/30 transition">
                </div>

                <div>
                    <label class="text-[10px] text-gray-500 ml-2 mb-1 block uppercase font-bold tracking-wider">Amount</label>
                    <input type="number" name="amount" placeholder="충전 금액 (₩)" required
                        class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-white/30 transition">
                </div>

                <button type="submit" class="w-full bg-white text-black font-bold py-3.5 rounded-xl mt-4 hover:opacity-90 transition shadow-lg text-sm">
                    진행하기
                </button>
            </form>
            
            <button onclick="history.back()" class="w-full text-gray-500 text-xs mt-6 hover:text-white transition">취소하고 돌아가기</button>
        </div>
    </div>
</body>
</html>
