<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>대시보드</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=DM+Mono&display=swap');

  /* 기본 색상 및 폰트 설정 */
  :root {
    --bg: #0a0a0a;
    --surface: #101010;
    --border: #222;
    --text-light: #ddd;
    --text-muted: #888;
    --green: #3ecf7a;
    --red: #ff4d4d;
    --font-main: 'DM Sans', sans-serif;
    --font-mono: 'DM Mono', monospace;
    --nav-height: 60px;
    --radius: 8px;
  }

  * {
    margin: 0; padding: 0; box-sizing: border-box;
  }
  body {
    background: var(--bg);
    color: var(--text-light);
    font-family: var(--font-main);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }
  a {
    color: var(--green);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }

  /* 상단 네비게이션 */
  nav {
    height: var(--nav-height);
    background: #050505;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 1000;
  }
  nav .nav-left, nav .nav-center, nav .nav-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  nav .brand {
    color: var(--green);
    font-weight: 700;
    font-size: 20px;
    letter-spacing: -1px;
    user-select: none;
  }
  nav a.nav-link {
    color: var(--text-muted);
    font-weight: 600;
    font-size: 14px;
    padding: 6px 10px;
    transition: background-color 0.15s, color 0.15s;
    border-radius: var(--radius);
  }
  nav a.nav-link.active, nav a.nav-link:hover {
    color: #fff;
    background: #171717;
  }

  /* 메인 컨텐츠 컨테이너 */
  main.page {
    max-width: 1200px;
    padding: 30px 24px;
    margin: 0 auto;
  }

  /* 환영 텍스트 영역 */
  .welcome {
    margin-bottom: 25px;
  }
  .welcome h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .welcome p {
    color: var(--text-muted);
    font-size: 15px;
    letter-spacing: 0.02em;
  }

  /* 통계 카드 그리드 */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
    margin-bottom: 30px;
  }
  .stat-card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 22px 24px;
    box-shadow: 0 1px 6px rgb(0 0 0 / 0.7);
  }
  .stat-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }
  .stat-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }
  .dot-green { background: var(--green); }
  .dot-white { background: #fff; }
  .stat-badge {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    color: var(--green);
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .stat-badge svg {
    width: 14px;
    height: 14px;
  }
  .stat-value {
    font-weight: 700;
    font-size: 32px;
    margin-bottom: 4px;
  }
  .stat-sub {
    font-size: 12px;
    color: var(--text-muted);
  }

  /* 차트 영역 */
  .chart-section {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 24px 28px 32px;
    margin-bottom: 36px;
    box-shadow: 0 1px 8px rgb(0 0 0 / 0.6);
  }
  .chart-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  .chart-head-left h3 {
    color: #eee;
    font-weight: 700;
    font-size: 18px;
    margin-bottom: 4px;
  }
  .chart-head-left p {
    color: var(--text-muted);
    font-size: 13px;
  }
  .chart-head-right {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    align-items: center;
  }
  .legend {
    display: flex;
    gap: 15px;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--text-muted);
  }
  .legend-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
  }

  .legend-dot.white { background: #fff; }
  .legend-dot.green { background: var(--green); }

  /* 차트 본문 캔버스 */
  .chart-wrap {
    position: relative;
    height: 280px;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .chart-tooltip {
    position: absolute;
    user-select: none;
    background: #181818;
    color: var(--green);
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 13px;
    padding: 10px 16px;
    border-radius: var(--radius);
    pointer-events: none;
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.15s ease;
    transform: translate(-50%, -130%);
    z-index: 10;
  }
  .chart-tooltip.visible {
    opacity: 1;
  }

  /* 거래 테이블 영역 */
  .deals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
    gap: 20px;
  }
  .deal-card {
    background: var(--surface);
    border-radius: var(--radius);
    box-shadow: 0 1px 8px rgb(0 0 0 / 0.6);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .deal-card-head {
    padding: 18px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .deal-card-title {
    font-weight: 700;
    font-size: 16px;
  }
  .deal-card-title span {
    font-weight: 400;
    color: var(--text-muted);
    margin-left: 8px;
    font-size: 13px;
  }
  .deal-table {
    width: 100%;
    border-collapse: collapse;
  }
  .deal-table th, .deal-table td {
    padding: 12px 24px;
    font-size: 13px;
    color: var(--text-light);
    border-bottom: 1px solid var(--border);
    user-select: text;
  }
  .deal-table th {
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-muted);
    font-size: 12px;
    letter-spacing: 0.07em;
  }
  .deal-table tbody tr:hover {
    background: #121212;
  }
  .user-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }
  .avatar {
    width: 34px;
    height: 34px;
    background: var(--bg);
    border-radius: 50%;
    border: 1.5px solid #121212;
    display: flex;
    justify-content: center;
    align-items: center;
    font-weight: 600;
    font-family: var(--font-mono);
    color: var(--green);
    user-select: none;
  }
  .coin-badge {
    background: #121212;
    border-radius: 20px;
    padding: 5px 14px;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 12px;
    color: var(--green);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .coin-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--green);
  }
  .amount {
    min-width: 65px;
    text-align: right;
  }
  .status-badge {
    font-weight: 600;
    font-size: 12px;
    padding: 5px 14px;
    border-radius: 20px;
    display: inline-block;
    user-select: none;
  }
  .status-open {
    background: rgba(255,255,255,0.08);
    color: #eee;
  }
  .status-closed {
    background: rgba(62,207,122,0.18);
    color: var(--green);
  }
  .add-deal {
    padding: 14px 24px;
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
    border-top: 1px solid var(--border);
  }
  .add-deal a {
    color: var(--green);
    font-weight: 700;
  }
  .add-deal a:hover {
    text-decoration: underline;
  }

  /* 버튼 */
  button.btn, button.btn-primary {
    cursor: pointer;
    border: none;
    outline: none;
  }
  button.btn {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-light);
    border-radius: var(--radius);
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background-color 0.2s;
  }
  button.btn:hover {
    background: var(--surface2);
  }
  button.btn svg {
    stroke: var(--text-light);
    width: 18px;
    height: 18px;
  }
  button.btn-primary {
    background: var(--green);
    color: #000;
    font-weight: 700;
    padding: 8px 22px;
    border-radius: var(--radius);
    display: flex;
    align-items: center;
    gap: 10px;
    transition: background-color 0.3s ease;
  }
  button.btn-primary svg {
    stroke: #000;
    width: 20px;
    height: 20px;
  }
  button.btn-primary:hover {
    background: #2db563;
  }

  /* 반응형 */
  @media (max-width: 1000px) {
    .stat-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .deals-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 480px) {
    nav {
      padding: 0 16px;
    }
    main.page {
      padding: 20px 16px;
    }
    .coin-badge {
      font-size: 11px;
      padding: 4px 12px;
    }
    .deal-card-title {
      font-size: 14px;
    }
    .deal-table th, .deal-table td {
      padding: 10px 12px;
      font-size: 11px;
    }
    button.btn, button.btn-primary {
      font-size: 12px;
      padding: 6px 14px;
    }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-left">
    <div class="brand" aria-label="브랜드 로고 및 이름">HalalMM</div>
    <a href="#" class="nav-link active">Dashboard</a>
    <a href="#" class="nav-link">Deals</a>
    <a href="#" class="nav-link">Support</a>
  </div>
  <div class="nav-right">
    <button aria-label="프로필 및 알림" class="btn">John Doe</button>
  </div>
</nav>

<main class="page">
  <section class="welcome">
    <div class="welcome-text">
      <h1>Welcome Back, John</h1>
      <p>View your current details and whats going on</p>
    </div>
    <div class="welcome-actions">
      <div class="search-box" role="search" aria-label="검색">
        <svg viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input type="search" placeholder="Search" aria-label="검색어 입력" style="all:unset; color:#aaa; font-size: 15px; width:130px;" />
      </div>
      <button class="btn" type="button" aria-label="지난 7일 보기">
        <svg viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        Last 7 days
      </button>
    </div>
  </section>

  <section class="stat-grid" aria-label="통계 카드">
    <article class="stat-card" role="region" aria-labelledby="stat1-title">
      <div class="stat-card-top">
        <div class="stat-label"><div class="dot dot-green"></div> Total Deals Completed</div>
        <div class="stat-badge">▲ 74.5%</div>
      </div>
      <div id="stat1-title" class="stat-value">2664</div>
      <div class="stat-sub">총 거래 완료</div>
    </article>
    <article class="stat-card" role="region" aria-labelledby="stat2-title">
      <div class="stat-card-top">
        <div class="stat-label"><div class="dot dot-green"></div> Total USD Value Dealt</div>
        <div class="stat-badge">▲ 74.5%</div>
      </div>
      <div id="stat2-title" class="stat-value">$14,899</div>
      <div class="stat-sub">이번 주 누적</div>
    </article>
    <article class="stat-card" role="region" aria-labelledby="stat3-title">
      <div class="stat-card-top">
        <div class="stat-label"><div class="dot dot-green"></div> Avg. Deal Length</div>
        <div class="stat-badge">▲ 74.5%</div>
      </div>
      <div id="stat3-title" class="stat-value">1.4<span style="font-weight:400; font-size:16px; color: var(--text-muted); margin-left:4px;">Days</span></div>
      <div class="stat-sub">평균 거래 기간</div>
    </article>
    <article class="stat-card" role="region" aria-labelledby="stat4-title">
      <div class="stat-card-top">
        <div class="stat-label"><div class="dot dot-green"></div> Deals in Progress</div>
        <div class="stat-badge">▲ 74.5%</div>
      </div>
      <div id="stat4-title" class="stat-value">2664</div>
      <div class="stat-sub">진행 중 거래</div>
    </article>
  </section>

  <section class="chart-section" aria-label="판매 완료 현황 차트">
    <div class="chart-head">
      <div>
        <h3>Completed Deals</h3>
        <p>Current sales and detailed trends</p>
      </div>
      <div class="chart-head-right">
        <div class="legend">
          <div class="legend-item"><div class="legend-dot white"></div> Completed Deals</div>
          <div class="legend-item"><div class="legend-dot green"></div> Avg. Deal Length</div>
        </div>
        <button class="btn" type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          Last 7 days
        </button>
      </div>
    </div>
    <div class="chart-wrap">
      <canvas id="chart" aria-label="Completed deals and average deal length chart"></canvas>
      <div id="tip" class="chart-tooltip" role="tooltip" aria-hidden="true"></div>
    </div>
  </section>

  <section class="deals-grid" aria-label="진행 중 주문과 완료 주문">
    <div class="deal-card" role="region" aria-labelledby="open-deals-title">
      <div class="deal-card-head">
        <h4 id="open-deals-title" class="deal-card-title">Open Deals <span>(3)</span></h4>
        <button class="btn" type="button">View All</button>
      </div>
      <table class="deal-table" role="table" aria-describedby="open-deals-desc" tabindex="0">
        <caption id="open-deals-desc" style="position:absolute; left:-9999px; top: auto; width:1px; height:1px; overflow:hidden;">Current open deals showing buyers, products, amount, and status.</caption>
        <thead>
          <tr>
            <th>Buyer</th><th>Product</th><th>Amount</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="KJ user">KJ</div>
                <div class="avatar" aria-label="MR user">MR</div>
                <span style="margin-left:10px;font-size:12px;">user#4821</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Sword Pack</div></td>
            <td class="amount">₩8,500</td>
            <td><span class="status-badge status-open">Open</span></td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="YS user">YS</div>
                <div class="avatar" aria-label="PK user">PK</div>
                <span style="margin-left:10px;font-size:12px;">user#3392</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>VIP Pass</div></td>
            <td class="amount">₩15,000</td>
            <td><span class="status-badge status-open">Open</span></td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="TH user">TH</div>
                <div class="avatar" aria-label="LM user">LM</div>
                <span style="margin-left:10px;font-size:12px;">user#7701</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Coin Pack x10</div></td>
            <td class="amount">₩5,200</td>
            <td><span class="status-badge status-open">Open</span></td>
          </tr>
        </tbody>
      </table>
      <div class="add-deal">Create another deal? <a href="#">Click here</a></div>
    </div>

    <div class="deal-card" role="region" aria-labelledby="closed-deals-title">
      <div class="deal-card-head">
        <h4 id="closed-deals-title" class="deal-card-title">Closed Deals <span>(10)</span></h4>
        <button class="btn" type="button">View All</button>
      </div>
      <table class="deal-table" role="table" aria-describedby="closed-deals-desc" tabindex="0">
        <caption id="closed-deals-desc" style="position:absolute; left:-9999px; top: auto; width:1px; height:1px; overflow:hidden;">Completed deals showing buyers, products, amount, and status.</caption>
        <thead>
          <tr>
            <th>Buyer</th><th>Product</th><th>Amount</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="AB user">AB</div><div class="avatar" aria-label="CD user">CD</div><span style="margin-left:10px;font-size:12px;">user#1012</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Sword Pack</div></td>
            <td class="amount">₩8,500</td>
            <td><span class="status-badge status-closed">Closed</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="EF user">EF</div><div class="avatar" aria-label="GH user">GH</div><span style="margin-left:10px;font-size:12px;">user#2234</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>VIP Pass</div></td>
            <td class="amount">₩15,000</td>
            <td><span class="status-badge status-closed">Closed</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="IJ user">IJ</div><div class="avatar" aria-label="KL user">KL</div><span style="margin-left:10px;font-size:12px;">user#3358</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Coin Pack x5</div></td>
            <td class="amount">₩2,900</td>
            <td><span class="status-badge status-closed">Closed</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="MN user">MN</div><div class="avatar" aria-label="OP user">OP</div><span style="margin-left:10px;font-size:12px;">user#4490</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Skin Pack</div></td>
            <td class="amount">₩11,200</td>
            <td><span class="status-badge status-closed">Closed</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="QR user">QR</div><div class="avatar" aria-label="ST user">ST</div><span style="margin-left:10px;font-size:12px;">user#5512</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>Sword Pack</div></td>
            <td class="amount">₩8,500</td>
            <td><span class="status-badge status-closed">Closed</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</main>

<script>
  // 모바일 메뉴 토글 (필요 시 해당 기능 추가 가능)
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');
  const mmOverlay = document.getElementById('mmOverlay');

  hamburger?.addEventListener('click', () => {
    if (!mobileMenu) return;
    const opened = mobileMenu.classList.toggle('open');
    mobileMenu.setAttribute('aria-hidden', opened ? 'false' : 'true');
  });
  mmOverlay?.addEventListener('click', () => {
    if (!mobileMenu) return;
    mobileMenu.classList.remove('open');
    mobileMenu.setAttribute('aria-hidden', 'true');
  });

  // 차트 그리기 로직
  const canvas = document.getElementById('chart');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    const tip = document.getElementById('tip');

    const sales = [12, 18, 22, 45, 58, 72, 80];
    const avg = [3, 5, 7, 12, 15, 18, 20];
    const xlabels = ['Feb 5', 'Feb 6', 'Feb 7', 'Feb 8', 'Feb 9', 'Feb 10', 'Feb 11'];
    const MINS = 0, MAXS = 90;
    const H = 260;
    const PAD = { l: 36, r: 16, t: 16, b: 36 };

    let CW = 0, PXs = [], PYs = [], PYa = [];
    let activeIdx = -1, tipX = 0, tipTX = 0, rafId = null;

    function buildPts() {
      const cW = CW - PAD.l - PAD.r;
      const cH = H - PAD.t - PAD.b;
      PXs = sales.map((_, i) => PAD.l + (i / (sales.length - 1)) * cW);
      PYs = sales.map(v => PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH);
      PYa = avg.map(v => PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH);
    }

    function drawArea(pts, color) {
      const cH = H - PAD.t - PAD.b;
      const grad = ctx.createLinearGradient(0, PAD.t, 0, PAD.t + cH);
      grad.addColorStop(0, color.replace('1)', '0.18)'));
      grad.addColorStop(1, color.replace('1)', '0)'));
      ctx.beginPath();
      ctx.moveTo(PXs[0], pts[0]);
      for (let i = 1; i < pts.length; i++) {
        const mx = (PXs[i - 1] + PXs[i]) / 2;
        ctx.bezierCurveTo(mx, pts[i - 1], mx, pts[i], PXs[i], pts[i]);
      }
      ctx.lineTo(PXs[pts.length - 1], PAD.t + cH);
      ctx.lineTo(PXs[0], PAD.t + cH);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
    }

    function drawLine(pts, color, w = 2) {
      ctx.beginPath();
      ctx.moveTo(PXs[0], pts[0]);
      for (let i = 1; i < pts.length; i++) {
        const mx = (PXs[i - 1] + PXs[i]) / 2;
        ctx.bezierCurveTo(mx, pts[i - 1], mx, pts[i], PXs[i], pts[i]);
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = w;
      ctx.lineJoin = 'round';
      ctx.stroke();
    }

    function draw(hi = -1) {
      const dpr = devicePixelRatio || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, CW, H);
      const cH = H - PAD.t - PAD.b;
      const font = "11px 'DM Sans', sans-serif";

      // 그리드
      ctx.strokeStyle = '#181818';
      ctx.lineWidth = 1;
      [0, 20, 40, 60, 80].forEach(v => {
        const yy = PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH;
        ctx.beginPath();
        ctx.moveTo(PAD.l, yy);
        ctx.lineTo(CW - PAD.r, yy);
        ctx.stroke();
      });

      // Y축 레이블
      ctx.font = font;
      ctx.fillStyle = '#444';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      [0, 20, 40, 60, 80].forEach(v => {
        const yy = PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH;
        ctx.fillText(v.toString(), PAD.l - 6, yy);
      });

      // X축 레이블
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = '#444';
      PXs.forEach((px, i) => ctx.fillText(xlabels[i], px, H - 8));

      // 활성점 가로선
      if (hi >= 0) {
        ctx.beginPath();
        ctx.moveTo(PXs[hi], PAD.t);
        ctx.lineTo(PXs[hi], PAD.t + cH);
        ctx.strokeStyle = 'rgba(255,255,255,0.1)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 그래프 영역들
      drawArea(PYs, 'rgba(255,255,255,1)');
      drawArea(PYa, 'rgba(62,207,122,1)');
      drawLine(PYa, '#3ecf7a', 2);
      drawLine(PYs, '#ffffff', 2.5);

      // 점들
      [[PYs, '#fff'], [PYa, '#3ecf7a']].forEach(([pts, col]) => {
        pts.forEach((py, i) => {
          const a = i === hi;
          ctx.beginPath();
          ctx.arc(PXs[i], py, a ? 5 : 3.5, 0, Math.PI * 2);
          ctx.fillStyle = col;
          ctx.fill();
          ctx.strokeStyle = '#000';
          ctx.lineWidth = a ? 2.5 : 1.5;
          ctx.stroke();
        });
      });
    }

    function resize() {
      CW = canvas.parentElement.clientWidth;
      const dpr = devicePixelRatio || 1;
      canvas.width = CW * dpr;
      canvas.height = H * dpr;
      canvas.style.width = CW + 'px';
      canvas.style.height = H + 'px';
      buildPts();
    }

    function animTip() {
      tipX += (tipTX - tipX) * 0.2;
      tip.style.left = tipX + 'px';
      if (Math.abs(tipTX - tipX) > 0.4) rafId = requestAnimationFrame(animTip);
      else rafId = null;
    }

    function nearest(cx) {
      const r = canvas.getBoundingClientRect();
      const mx = (cx - r.left) / r.width * CW;
      let bi = -1, bd = 9999;
      PXs.forEach((px, i) => {
        const d = Math.abs(mx - px);
        if (d < bd) {
          bd = d;
          bi = i;
        }
      });
      return bd < CW / sales.length ? bi : -1;
    }

    function showTip(idx) {
      if (idx < 0) { hideTip(); return; }
      activeIdx = idx;
      const r = canvas.getBoundingClientRect();
      const sx = r.width / CW, sy = r.height / H;
      tipTX = PXs[idx] * sx;
      const ty = PYs[idx] * sy;
      if (!tip.classList.contains('visible')) { tipX = tipTX; tip.style.left = tipX + 'px'; }
      tip.style.top = (ty - 10) + 'px';
      tip.textContent = `${xlabels[idx]} 판매 ${sales[idx]}건 / 처리 ${avg[idx]}건`;
      tip.classList.add('visible');
      tip.setAttribute('aria-hidden', 'false');
      if (!rafId) rafId = requestAnimationFrame(animTip);
      draw(idx);
    }

    function hideTip() {
      activeIdx = -1;
      tip.classList.remove('visible');
      tip.setAttribute('aria-hidden', 'true');
      draw(-1);
    }

    canvas.addEventListener('mousemove', e => showTip(nearest(e.clientX)));
    canvas.addEventListener('mouseleave', hideTip);
    canvas.addEventListener('touchstart', e => { e.preventDefault(); showTip(nearest(e.touches[0].clientX)); }, { passive: false });
    canvas.addEventListener('touchmove', e => { e.preventDefault(); showTip(nearest(e.touches[0].clientX)); }, { passive: false });
    canvas.addEventListener('touchend', () => setTimeout(hideTip, 1800));

    resize();
    draw();
    window.addEventListener('resize', () => { resize(); draw(activeIdx); });
  }
</script>
</body>
</html>
