<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>입금 안내 - 세일러 피스</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.06); }
    </style>
</head>
<body>
    <div class="max-w-md w-full p-6">
        <div class="glass-card p-8 rounded-[32px]">
            <div class="text-center mb-8">
                <div class="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/5">
                    <i class="fa-solid fa-university text-xl text-gray-400"></i>
                </div>
                <h2 class="text-2xl font-bold mb-1">입금 안내</h2>
                <p class="text-gray-500 text-xs">{{ depositor }}님, 아래 계좌로 입금해 주세요.</p>
            </div>

            <div class="space-y-4 bg-white/[0.02] p-6 rounded-2xl border border-white/5 mb-8">
                <div class="flex justify-between items-center">
                    <span class="text-[11px] text-gray-500 font-bold uppercase">Bank</span>
                    <span class="text-sm font-semibold">{{ bank.bank }}</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-[11px] text-gray-500 font-bold uppercase">Account</span>
                    <span class="text-sm font-semibold text-blue-400 underline decoration-blue-400/30 underline-offset-4">{{ bank.account }}</span>
                </div>
                <div class="flex justify-between items-center">
                    <span class="text-[11px] text-gray-500 font-bold uppercase">Owner</span>
                    <span class="text-sm font-semibold">{{ bank.owner }}</span>
                </div>
                <div class="pt-4 border-t border-white/5 flex justify-between items-center">
                    <span class="text-[11px] text-gray-500 font-bold uppercase">Pay</span>
                    <span class="text-lg font-bold text-white">{{ "{:,}".format(amount|int) }}₩</span>
                </div>
            </div>

            <button onclick="location.href='/'" class="w-full bg-white/5 border border-white/10 text-white font-bold py-3.5 rounded-xl hover:bg-white/10 transition text-sm">
                입금 완료 확인
            </button>
        </div>
    </div>
</body>
</html>
