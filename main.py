<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>입금 대기 - 세일러 피스</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #000; color: #fff; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .glass-card { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.06); }
        .loading-dots::after { content: ' .'; animation: dots 1.5s steps(5, end) infinite; }
        @keyframes dots { 0%, 20% { content: ' .'; } 40% { content: ' ..'; } 60% { content: ' ...'; } 80%, 100% { content: ''; } }
    </style>
</head>
<body>
    <div class="max-w-md w-full p-6" id="content-area">
        <div class="glass-card p-8 rounded-[32px]">
            <div class="text-center mb-8">
                <div class="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/5">
                    <i class="fa-solid fa-spinner fa-spin text-xl text-blue-400"></i>
                </div>
                <h2 class="text-2xl font-bold mb-1">입금 대기 중</h2>
                <p class="text-gray-500 text-xs loading-dots">시스템이 입금을 자동으로 확인하고 있습니다</p>
            </div>

            <div class="space-y-4 bg-white/[0.02] p-6 rounded-2xl border border-white/5 mb-6">
                <div class="flex justify-between items-center"><span class="text-[11px] text-gray-500 font-bold">은행명</span><span class="text-sm font-semibold">{{ bank.bank }}</span></div>
                <div class="flex justify-between items-center"><span class="text-[11px] text-gray-500 font-bold">계좌번호</span><span class="text-sm font-semibold text-blue-400">{{ bank.account }}</span></div>
                <div class="flex justify-between items-center"><span class="text-[11px] text-gray-500 font-bold">예금주</span><span class="text-sm font-semibold">{{ bank.owner }}</span></div>
                <div class="pt-4 border-t border-white/5 flex justify-between items-center"><span class="text-[11px] text-gray-500 font-bold">입금액</span><span class="text-lg font-bold text-white">{{ amount }}₩</span></div>
            </div>

            <div class="text-[10px] text-gray-500 leading-relaxed space-y-1 bg-white/5 p-4 rounded-xl">
                <p>• 반드시 입력하신 <span class="text-white font-bold">{{ name }}</span> 성함으로 입금해주세요.</p>
                <p>• 5분 이내에 입금이 확인되지 않으면 신청이 자동 취소됩니다.</p>
                <p>• 타인 명의 입금 시 확인이 늦어질 수 있습니다.</p>
            </div>
        </div>
    </div>

    <script>
        const name = "{{ name }}";
        const amount = "{{ amount }}";
        
        async function checkStatus() {
            try {
                const response = await fetch(`/check_status/${name}/${amount}`);
                const data = await response.json();
                
                if (data.status === "success") {
                    document.getElementById('content-area').innerHTML = `
                        <div class="glass-card p-8 rounded-[32px] text-center">
                            <div class="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i class="fa-solid fa-check text-2xl text-green-500"></i>
                            </div>
                            <h2 class="text-2xl font-bold mb-2">충전 완료</h2>
                            <p class="text-gray-400 text-sm mb-6">포인트가 성공적으로 지급되었습니다.</p>
                            <button onclick="location.href='/'" class="w-full bg-white text-black font-bold py-3.5 rounded-xl">상점으로 돌아가기</button>
                        </div>
                    `;
                } else if (data.status === "expired") {
                    alert("시간이 만료되어 취소되었습니다. 다시 신청해주세요.");
                    location.href = "/change";
                }
            } catch (e) { console.error("확인 중 오류 발생"); }
        }

        // 3초마다 상태 체크
        setInterval(checkStatus, 3000);
    </script>
</body>
</html>
