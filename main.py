<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>구매로그</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: #080910;
            color: #e2e4f0;
            font-family: 'Noto Sans KR', sans-serif;
            min-height: 100vh;
        }

        body::before {
            content: '';
            position: fixed;
            width: 700px;
            height: 500px;
            background: radial-gradient(ellipse, rgba(88,101,242,0.1) 0%, transparent 65%);
            top: -80px;
            left: 50%;
            transform: translateX(-50%);
            pointer-events: none;
            z-index: 0;
        }

        .wrap {
            max-width: 700px;
            margin: 0 auto;
            padding: 48px 16px 80px;
            position: relative;
            z-index: 1;
        }

        /* 헤더 */
        .top {
            margin-bottom: 36px;
            animation: up 0.5s ease both;
        }

        .live-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            background: rgba(88,101,242,0.1);
            border: 1px solid rgba(88,101,242,0.22);
            border-radius: 99px;
            padding: 5px 14px 5px 10px;
            font-size: 11px;
            font-weight: 700;
            color: #8891f5;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 16px;
        }

        .live-dot {
            width: 7px;
            height: 7px;
            background: #3ecf8e;
            border-radius: 50%;
            box-shadow: 0 0 6px #3ecf8e;
            animation: blink 2s infinite;
        }

        .top h1 {
            font-size: 30px;
            font-weight: 900;
            color: #fff;
            letter-spacing: -0.03em;
        }

        .top h1 span { color: #7983f5; }

        .top p {
            font-size: 13px;
            color: #4a4d65;
            margin-top: 7px;
            font-weight: 500;
        }

        /* 통계 */
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 28px;
            animation: up 0.5s ease 0.08s both;
        }

        .stat {
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 20px;
            padding: 16px 12px;
            text-align: center;
        }

        .stat-num {
            font-size: 20px;
            font-weight: 900;
            color: #7983f5;
            letter-spacing: -0.02em;
        }

        .stat-lbl {
            font-size: 10px;
            color: #3e4258;
            font-weight: 600;
            margin-top: 5px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        /* 카드 리스트 */
        .list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* 카드 - 참고 이미지 스타일 */
        .card {
            background: linear-gradient(135deg, rgba(20,22,38,0.95) 0%, rgba(14,16,28,0.98) 100%);
            border: 1px solid rgba(88,101,242,0.18);
            border-left: 3px solid rgba(88,101,242,0.5);
            border-radius: 18px;
            padding: 16px 20px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
            animation: up 0.4s ease both;
        }

        .card::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, rgba(88,101,242,0.04) 0%, transparent 50%);
            pointer-events: none;
            border-radius: inherit;
        }

        .card:hover {
            border-color: rgba(88,101,242,0.4);
            border-left-color: rgba(88,101,242,0.8);
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(88,101,242,0.12), 0 0 0 1px rgba(88,101,242,0.1);
        }

        .card.new {
            animation: newIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both;
        }

        /* 카드 상단 - 아바타 + 이름 + 가격 */
        .card-top {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }

        .avatar {
            width: 46px;
            height: 46px;
            border-radius: 12px;
            object-fit: cover;
            background: rgba(88,101,242,0.1);
            border: 1px solid rgba(88,101,242,0.2);
            flex-shrink: 0;
        }

        .name-wrap { flex: 1; min-width: 0; }

        .uname {
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.01em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .uid {
            font-size: 11px;
            color: #3e4258;
            font-weight: 500;
            margin-top: 2px;
        }

        .price {
            font-size: 20px;
            font-weight: 900;
            color: #5cf5c0;
            letter-spacing: -0.02em;
            flex-shrink: 0;
        }

        /* 카드 하단 - 게임패스 이름 + 시간 */
        .card-bottom { padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); }

        .gprow {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
        }

        .gpname {
            font-size: 14px;
            font-weight: 700;
            color: #c8ccee;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 70%;
        }

        .gpname span {
            color: #7983f5;
        }

        .rbadge {
            background: rgba(88,101,242,0.12);
            border: 1px solid rgba(88,101,242,0.2);
            border-radius: 8px;
            padding: 2px 9px;
            font-size: 11px;
            font-weight: 700;
            color: #7983f5;
            white-space: nowrap;
        }

        .meta {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .ok-dot {
            width: 5px;
            height: 5px;
            background: #3ecf8e;
            border-radius: 50%;
            box-shadow: 0 0 4px #3ecf8e;
            flex-shrink: 0;
        }

        .ok-txt { font-size: 11px; color: #3ecf8e; font-weight: 700; }
        .sep { font-size: 11px; color: #2a2d3e; }
        .time-txt { font-size: 11px; color: #3e4258; font-weight: 500; }

        /* 빈/로딩 */
        .center {
            text-align: center;
            padding: 72px 20px;
            color: #3e4258;
        }

        .center h3 {
            font-size: 16px;
            font-weight: 700;
            color: #555871;
            margin-bottom: 6px;
        }

        .center p { font-size: 13px; }

        .spinner {
            width: 28px;
            height: 28px;
            border: 2px solid rgba(88,101,242,0.15);
            border-top-color: #5865f2;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            margin: 0 auto 14px;
        }

        /* 더보기 */
        .more-btn {
            display: block;
            width: 100%;
            margin-top: 10px;
            padding: 14px;
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            color: #7983f5;
            font-size: 13px;
            font-weight: 700;
            font-family: 'Noto Sans KR', sans-serif;
            cursor: pointer;
            transition: background 0.2s, border-color 0.2s;
        }

        .more-btn:hover {
            background: rgba(88,101,242,0.08);
            border-color: rgba(88,101,242,0.25);
        }

        @keyframes up {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes newIn {
            from { opacity: 0; transform: scale(0.95) translateY(-12px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        @media (max-width: 480px) {
            .top h1 { font-size: 24px; }
            .stat-num { font-size: 17px; }
            .price { font-size: 17px; }
            .uname { font-size: 14px; }
            .gpname { font-size: 13px; }
        }
    </style>
</head>
<body>
<div class="wrap">

    <div class="top">
        <div class="live-pill">
            <div class="live-dot"></div>
            LIVE
        </div>
        <h1>실시간 <span>구매로그</span></h1>
        <p>최근 구매 내역을 실시간으로 확인하세요</p>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-num" id="sTot">—</div>
            <div class="stat-lbl">총 구매</div>
        </div>
        <div class="stat">
            <div class="stat-num" id="sToday">—</div>
            <div class="stat-lbl">오늘</div>
        </div>
        <div class="stat">
            <div class="stat-num" id="sAmt">—</div>
            <div class="stat-lbl">총 매출</div>
        </div>
    </div>

    <div class="list" id="list">
        <div class="center">
            <div class="spinner"></div>
            <p>불러오는 중...</p>
        </div>
    </div>

    <button class="more-btn" id="moreBtn" style="display:none" onclick="loadMore()">더보기</button>

</div>
<script>
    let page = 0, loading = false, hasMore = true;
    const LIMIT = 20;
    const seen = new Set();

    function timeAgo(str) {
        const d = new Date(str), now = new Date();
        const m = Math.floor((now - d) / 60000);
        if (m < 1) return '방금 전';
        if (m < 60) return m + '분 전';
        const h = Math.floor(m / 60);
        if (h < 24) return h + '시간 전';
        const days = Math.floor(h / 24);
        if (days < 7) return days + '일 전';
        return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function fmtAmt(n) {
        if (n >= 10000) return (n / 10000).toFixed(1) + '만';
        return n.toLocaleString();
    }

    function makeCard(log, isNew) {
        const card = document.createElement('div');
        card.className = 'card' + (isNew ? ' new' : '');
        card.dataset.id = log.order_id;

        const av = log.avatar_url
            || `https://www.roblox.com/headshot-thumbnail/image?userId=${log.roblox_id||1}&width=150&height=150&format=png`;

        const robuxStr = log.robux
            ? `<span class="rbadge">R$ ${Number(log.robux).toLocaleString()}</span>`
            : '';

        card.innerHTML = `
            <div class="card-top">
                <img class="avatar" src="${av}"
                    onerror="this.src='https://tr.rbxcdn.com/53eb9b17fe1432a809c73a13889b5006/150/150/Image/Png'"
                    alt="">
                <div class="name-wrap">
                    <div class="uname">${log.roblox_name || '유저'}</div>
                    <div class="uid">#${(log.order_id || '').substring(0, 8)}</div>
                </div>
                <div class="price">${log.amount ? log.amount.toLocaleString() + '원' : ''}</div>
            </div>
            <div class="card-bottom">
                <div class="gprow">
                    <span class="gpname">${log.gamepass_name || '게임패스'}</span>
                    ${robuxStr}
                </div>
                <div class="meta">
                    <div class="ok-dot"></div>
                    <span class="ok-txt">구매 완료</span>
                    <span class="sep">·</span>
                    <span class="time-txt">${timeAgo(log.created_at)}</span>
                </div>
            </div>
        `;
        return card;
    }

    function updateStats(s) {
        if (!s) return;
        document.getElementById('sTot').textContent = (s.total || 0).toLocaleString();
        document.getElementById('sToday').textContent = (s.today || 0).toLocaleString();
        document.getElementById('sAmt').textContent = fmtAmt(s.total_amount || 0) + '원';
    }

    async function load() {
        if (loading) return;
        loading = true;
        try {
            const r = await fetch(`/api/purchase-logs?limit=${LIMIT}&offset=0`);
            const data = await r.json();
            updateStats(data.stats);
            const list = document.getElementById('list');
            if (!data.logs?.length) {
                list.innerHTML = `<div class="center"><h3>구매 내역이 없습니다</h3><p>첫 번째 구매를 기다리고 있어요</p></div>`;
                return;
            }
            list.innerHTML = '';
            data.logs.forEach((log, i) => {
                const c = makeCard(log, false);
                c.style.animationDelay = i * 40 + 'ms';
                list.appendChild(c);
                seen.add(log.order_id);
            });
            page = 1;
            hasMore = data.logs.length >= LIMIT;
            document.getElementById('moreBtn').style.display = hasMore ? 'block' : 'none';
        } catch {
            document.getElementById('list').innerHTML = `<div class="center"><h3>불러오기 실패</h3><p>잠시 후 다시 시도해주세요</p></div>`;
        } finally { loading = false; }
    }

    async function loadMore() {
        if (loading || !hasMore) return;
        loading = true;
        const btn = document.getElementById('moreBtn');
        btn.textContent = '불러오는 중...';
        try {
            const r = await fetch(`/api/purchase-logs?limit=${LIMIT}&offset=${page * LIMIT}`);
            const data = await r.json();
            const list = document.getElementById('list');
            data.logs.forEach(log => {
                list.appendChild(makeCard(log, false));
                seen.add(log.order_id);
            });
            page++;
            hasMore = data.logs.length >= LIMIT;
            btn.style.display = hasMore ? 'block' : 'none';
            btn.textContent = '더보기';
        } catch { btn.textContent = '더보기'; }
        finally { loading = false; }
    }

    async function poll() {
        try {
            const r = await fetch(`/api/purchase-logs?limit=${LIMIT}&offset=0`);
            const data = await r.json();
            updateStats(data.stats);
            const list = document.getElementById('list');
            (data.logs || []).filter(l => !seen.has(l.order_id)).reverse().forEach(log => {
                const c = makeCard(log, true);
                list.insertBefore(c, list.firstChild);
                seen.add(log.order_id);
            });
        } catch {}
    }

    load();
    setInterval(poll, 20000);
</script>
</body>
</html>
