<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>구매로그</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #07080f;
  --surface: #0d0f1c;
  --surface2: #121428;
  --border: rgba(88,101,242,0.13);
  --border-h: rgba(88,101,242,0.3);
  --text: #c8ccf0;
  --muted: #3a3d5c;
  --accent: #5865F2;
  --accent-bright: #8891f5;
  --accent-soft: rgba(88,101,242,0.12);
  --ok: #a5b4ff;
  --mono: 'DM Mono', monospace;
  --display: 'Syne', sans-serif;
  --body: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--body);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

body::before {
  content: '';
  position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none; z-index: 0;
}

body::after {
  content: '';
  position: fixed;
  top: -300px; left: 50%;
  transform: translateX(-50%);
  width: 800px; height: 600px;
  background: radial-gradient(ellipse, rgba(88,101,242,0.09) 0%, transparent 65%);
  pointer-events: none; z-index: 0;
}

.shell {
  max-width: 720px;
  margin: 0 auto;
  padding: 56px 24px 100px;
  position: relative; z-index: 1;
}

/* ── 헤더 ── */
header {
  margin-bottom: 44px;
  animation: fadeUp 0.6s cubic-bezier(0.22,1,0.36,1) both;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 18px;
}

/* 연두 없애고 블루루퍼트 계열 dot */
.live-dot {
  width: 7px; height: 7px;
  background: var(--accent-bright);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2.4s ease-in-out infinite;
}

h1 {
  font-family: var(--display);
  font-size: clamp(36px, 7vw, 50px);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
  color: #fff;
  margin-bottom: 12px;
}

h1 em { font-style: normal; color: var(--accent-bright); }

.sub { font-size: 15px; color: var(--muted); font-weight: 400; }

.divider {
  height: 1px;
  background: linear-gradient(90deg, var(--border-h) 0%, transparent 100%);
  margin-bottom: 32px;
}

/* ── 통계 ── */
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
  margin-bottom: 36px;
  background: var(--border);
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid var(--border);
  animation: fadeUp 0.6s cubic-bezier(0.22,1,0.36,1) 0.07s both;
}

.stat {
  background: var(--surface);
  padding: 24px 16px;
  text-align: center;
  transition: background 0.2s;
}

.stat:hover { background: var(--surface2); }

.stat-n {
  font-family: var(--display);
  font-size: 28px;
  font-weight: 800;
  color: var(--accent-bright);
  letter-spacing: -0.03em;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-l {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

/* ── 피드 ── */
.feed { display: flex; flex-direction: column; gap: 3px; }

/* ── 카드 ── */
.card {
  background: var(--surface);
  border-radius: 16px;
  padding: 20px 22px;
  position: relative;
  overflow: hidden;
  transition: background 0.18s, transform 0.18s, box-shadow 0.18s, border-color 0.18s;
  animation: fadeUp 0.5s cubic-bezier(0.22,1,0.36,1) both;
  border: 1px solid transparent;
}

.card::before {
  content: '';
  position: absolute;
  left: 0; top: 14px; bottom: 14px;
  width: 3px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
  opacity: 0;
  transition: opacity 0.18s;
  box-shadow: 0 0 12px var(--accent);
}

.card:hover {
  background: var(--surface2);
  transform: translateX(4px);
  border-color: var(--border);
  box-shadow: 0 4px 40px rgba(88,101,242,0.08);
}

.card:hover::before { opacity: 1; }

.card.entering {
  animation: slideIn 0.45s cubic-bezier(0.34,1.56,0.64,1) both;
}

.card-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-wrap { position: relative; flex-shrink: 0; }

.avatar {
  width: 52px; height: 52px;
  border-radius: 12px;
  object-fit: cover;
  background: var(--surface2);
  display: block;
  border: 1px solid var(--border);
}

/* 아바타 배지 → 블루 계열 */
.av-badge {
  position: absolute;
  bottom: -3px; right: -3px;
  width: 16px; height: 16px;
  background: var(--bg);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}

.av-dot {
  width: 9px; height: 9px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--accent);
}

.card-info { flex: 1; min-width: 0; }

.card-name {
  font-size: 16px;
  font-weight: 700;
  color: #eceeff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.card-id {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.06em;
}

.card-right { text-align: right; flex-shrink: 0; }

.card-price {
  font-family: var(--display);
  font-size: 22px;
  font-weight: 800;
  color: var(--accent-bright);
  letter-spacing: -0.02em;
  line-height: 1;
  margin-bottom: 4px;
}

.card-robux {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

.card-foot {
  margin-top: 14px;
  padding-top: 13px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.gamepass-name {
  font-size: 13px;
  font-weight: 500;
  color: #4a4e78;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}

/* 완료 뱃지 → 블루 계열 */
.ok-label {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ok);
  background: rgba(88,101,242,0.1);
  border: 1px solid rgba(88,101,242,0.25);
  border-radius: 5px;
  padding: 3px 7px;
}

.time-label {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.04em;
}

/* ── 상태 ── */
.state-box {
  padding: 80px 20px;
  text-align: center;
  color: var(--muted);
}

.loader {
  width: 26px; height: 26px;
  border: 2px solid rgba(88,101,242,0.12);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 16px;
}

.state-box h3 {
  font-family: var(--display);
  font-size: 18px;
  font-weight: 700;
  color: #1e2040;
  margin-bottom: 6px;
}

.state-box p { font-size: 13px; }

/* ── 더보기 ── */
.more-btn {
  display: block;
  width: 100%;
  margin-top: 3px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}

.more-btn:hover {
  background: var(--surface2);
  color: var(--accent-bright);
  border-color: var(--border-h);
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.75); }
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 480px) {
  h1 { font-size: 30px; }
  .stat-n { font-size: 22px; }
  .card-price { font-size: 18px; }
  .card-name { font-size: 14px; }
  .avatar { width: 44px; height: 44px; }
  .shell { padding: 36px 14px 80px; }
}
</style>
</head>
<body>
<div class="shell">

  <header>
    <div class="eyebrow">
      <span class="live-dot"></span>
      실시간 업데이트
    </div>
    <h1>구매 <em>로그</em></h1>
    <p class="sub">모든 거래 내역을 실시간으로 확인합니다</p>
  </header>

  <div class="divider"></div>

  <div class="stats">
    <div class="stat">
      <div class="stat-n" id="sTot">—</div>
      <div class="stat-l">총 거래</div>
    </div>
    <div class="stat">
      <div class="stat-n" id="sToday">—</div>
      <div class="stat-l">오늘</div>
    </div>
    <div class="stat">
      <div class="stat-n" id="sAmt">—</div>
      <div class="stat-l">누적 매출</div>
    </div>
  </div>

  <div class="feed" id="feed">
    <div class="state-box">
      <div class="loader"></div>
      <p>불러오는 중...</p>
    </div>
  </div>

  <button class="more-btn" id="moreBtn" style="display:none" onclick="loadMore()">더보기 ↓</button>

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
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

function fmtAmt(n) {
  if (n >= 100000000) return (n / 100000000).toFixed(1) + '억';
  if (n >= 10000) return Math.floor(n / 10000) + '만';
  return n.toLocaleString();
}

function makeCard(log, isNew) {
  const el = document.createElement('div');
  el.className = 'card' + (isNew ? ' entering' : '');
  el.dataset.id = log.order_id;
  const av = log.avatar_url ||
    `https://www.roblox.com/headshot-thumbnail/image?userId=${log.roblox_id || 1}&width=150&height=150&format=png`;
  el.innerHTML = `
    <div class="card-row">
      <div class="avatar-wrap">
        <img class="avatar" src="${av}"
          onerror="this.src='https://tr.rbxcdn.com/53eb9b17fe1432a809c73a13889b5006/150/150/Image/Png'" alt="">
        <div class="av-badge"><div class="av-dot"></div></div>
      </div>
      <div class="card-info">
        <div class="card-name">${log.roblox_name || '유저'}</div>
        <div class="card-id">#${(log.order_id || '').substring(0, 8).toUpperCase()}</div>
      </div>
      <div class="card-right">
        <div class="card-price">${log.amount ? log.amount.toLocaleString() + '원' : ''}</div>
        <div class="card-robux">${log.robux ? 'R$ ' + Number(log.robux).toLocaleString() : ''}</div>
      </div>
    </div>
    <div class="card-foot">
      <span class="gamepass-name">${log.gamepass_name || '게임패스'}</span>
      <div class="card-meta">
        <span class="ok-label">완료</span>
        <span class="time-label">${timeAgo(log.created_at)}</span>
      </div>
    </div>`;
  return el;
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
    const feed = document.getElementById('feed');
    if (!data.logs?.length) {
      feed.innerHTML = `<div class="state-box"><h3>내역 없음</h3><p>첫 번째 거래를 기다리고 있습니다</p></div>`;
      return;
    }
    feed.innerHTML = '';
    data.logs.forEach((log, i) => {
      const c = makeCard(log, false);
      c.style.animationDelay = i * 35 + 'ms';
      feed.appendChild(c);
      seen.add(log.order_id);
    });
    page = 1;
    hasMore = data.logs.length >= LIMIT;
    document.getElementById('moreBtn').style.display = hasMore ? 'block' : 'none';
  } catch {
    document.getElementById('feed').innerHTML =
      `<div class="state-box"><h3>오류 발생</h3><p>잠시 후 다시 시도해주세요</p></div>`;
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
    const feed = document.getElementById('feed');
    data.logs.forEach(log => {
      if (!seen.has(log.order_id)) { feed.appendChild(makeCard(log, false)); seen.add(log.order_id); }
    });
    page++;
    hasMore = data.logs.length >= LIMIT;
    btn.style.display = hasMore ? 'block' : 'none';
    btn.textContent = '더보기 ↓';
  } catch { btn.textContent = '더보기 ↓'; }
  finally { loading = false; }
}

async function poll() {
  try {
    const r = await fetch(`/api/purchase-logs?limit=${LIMIT}&offset=0`);
    const data = await r.json();
    updateStats(data.stats);
    const feed = document.getElementById('feed');
    (data.logs || []).filter(l => !seen.has(l.order_id)).reverse().forEach(log => {
      const c = makeCard(log, true);
      feed.insertBefore(c, feed.firstChild);
      seen.add(log.order_id);
    });
  } catch {}
}

load();
setInterval(poll, 15000);
</script>
</body>
</html>
