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
        
        /* 라이트 모드 대응 (필요시) */
        body.light-mode { background-color: #fff !important; color: #000 !important; }
        body.light-mode .glass-card { background: rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.1); }
        body.light-mode input { background: rgba(0, 0, 0, 0.05); border: 1px solid rgba(0, 0, 0, 0.1); color: #000; }
        body.light-mode .buy-btn { background: #000 !important; color: #fff !important; }
    </style>
</head>
<body>
    <div class="max-w-md w-full p-6">
        <div class="glass-card p-8 rounded-[32px]">
            <div class="text-center mb-8">
                <h2 class="text-2xl font-bold mb-2">포인트 충전</h2>
                <p class="text-gray-500 text-sm">입금 정보를 정확하게 입력해 주세요.</p>
            </div>

            <form action="/change/api" method="POST" class="space-y-5">
                <div>
                    <label class="text-[11px] text-gray-400 ml-2 mb-1.5 block font-bold tracking-tight">입금자 성함</label>
                    <input type="text" name="depositor" placeholder="실제 입금하실 성함" required
                        class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white/30 transition">
                </div>

                <div>
                    <label class="text-[11px] text-gray-400 ml-2 mb-1.5 block font-bold tracking-tight">충전 신청 금액</label>
                    <input type="number" name="amount" placeholder="금액을 숫자로만 입력 (예: 10000)" required
                        class="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white/30 transition">
                </div>

                <button type="submit" class="w-full bg-white text-black font-bold py-4 rounded-xl mt-4 hover:opacity-90 transition shadow-lg text-sm">
                    충전 진행하기
                </button>
            </form>

            <div class="mt-8 pt-6 border-t border-white/5">
                <div class="bg-white/5 p-4 rounded-2xl">
                    <h4 class="text-[11px] font-bold text-gray-400 mb-2">충전 전 주의사항</h4>
                    <ul class="text-[10px] text-gray-500 space-y-1.5 leading-relaxed">
                        <li>• 신청하신 금액과 실제 입금액이 일치해야 자동 승인됩니다.</li>
                        <li>• 입금 확인은 평균 1~3분 정도 소요됩니다.</li>
                        <li>• 5분이 지나도 충전이 안 될 경우 고객센터로 문의하세요.</li>
                    </ul>
                </div>
            </div>
            
            <button onclick="location.href='/'" class="w-full text-gray-500 text-xs mt-6 hover:text-white transition">취소하고 상점으로 돌아가기</button>
        </div>
    </div>
</body>
</html>
