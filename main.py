<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RobloxStore - 대시보드</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg: #000000;
    --sidebar-bg: #000000;
    --card-bg: #0d0d0d;
    --card-border: #1e1e1e;
    --text-primary: #ffffff;
    --text-secondary: #777;
    --text-muted: #444;
    --accent: #ffffff;
    --accent-hover: #e0e0e0;
    --green: #4caf7d;
    --yellow: #e8b84b;
    --blue: #4a9eff;
    --sidebar-width: 190px;
    --header-height: 56px;
  }

  body {
    background: var(--bg);
    color: var(--text-primary);
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* HEADER */
  header {
    height: var(--header-height);
    background: #000;
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 100;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 15px;
    letter-spacing: -0.3px;
  }

  .logo-icon {
    width: 30px; height: 30px;
    background: #ffffff;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
  }

  .logo-icon svg { width: 16px; height: 16px; fill: none; stroke: #000; stroke-width: 2; }

  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .header-btn {
    width: 32px; height: 32px;
    background: #0d0d0d;
    border: 1px solid #1e1e1e;
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    color: var(--text-secondary);
    transition: all 0.15s;
  }

  .header-btn:hover { background: #1a1a1a; color: var(--text-primary); }

  .status-dot {
    width: 8px; height: 8px;
    background: var(--green);
    border-radius: 50%;
    box-shadow: 0 0 6px var(--green);
  }

  /* LAYOUT */
  .layout {
    display: flex;
    margin-top: var(--header-height);
    min-height: calc(100vh - var(--header-height));
  }

  /* SIDEBAR */
  aside {
    width: var(--sidebar-width);
    background: var(--sidebar-bg);
    border-right: 1px solid #1a1a1a;
    position: fixed;
    top: var(--header-height);
    left: 0;
    height: calc(100vh - var(--header-height));
    display: flex;
    flex-direction: column;
    padding: 16px 0;
    overflow-y: auto;
    z-index: 50;
    transition: transform 0.25s ease;
  }

  .nav-section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    text-transform: uppercase;
    padding: 0 16px 6px;
    margin-top: 12px;
  }

  .nav-section-label:first-child { margin-top: 0; }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 14px;
    margin: 0 8px;
    border-radius: 8px;
    cursor: pointer;
    color: var(--text-secondary);
    font-size: 13px;
    transition: all 0.15s;
    text-decoration: none;
    user-select: none;
  }

  .nav-item:hover { background: #111; color: var(--text-primary); }

  .nav-item.active {
    background: #141414;
    color: var(--text-primary);
    border: 1px solid #252525;
  }

  .nav-item svg { width: 15px; height: 15px; flex-shrink: 0; }

  .nav-bottom {
    margin-top: auto;
    padding-top: 12px;
    border-top: 1px solid #1a1a1a;
  }

  .nav-item.danger { color: #ff4444; }
  .nav-item.danger:hover { background: rgba(255,68,68,0.08); }

  /* MAIN */
  main {
    margin-left: var(--sidebar-width);
    flex: 1;
    padding: 28px;
    min-width: 0;
  }

  .page-title {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 4px;
  }

  .page-title svg { width: 18px; height: 18px; color: var(--text-secondary); }

  .page-subtitle {
    color: var(--text-secondary);
    font-size: 13px;
    margin-bottom: 24px;
  }

  /* STAT CARDS */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 20px;
  }

  .stat-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 20px 22px;
  }

  .stat-label {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 10px;
  }

  .stat-label svg { width: 13px; height: 13px; }

  .stat-value {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1;
    margin-bottom: 7px;
  }

  .stat-change {
    font-size: 12px;
    color: var(--green);
    font-weight: 500;
  }

  /* CHART */
  .chart-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 20px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
  }

  .card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 600;
  }

  .card-title svg { width: 14px; height: 14px; color: var(--text-secondary); }

  .period-select {
    background: #000;
    border: 1px solid #222;
    color: var(--text-primary);
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 7px;
    cursor: pointer;
    outline: none;
  }

  .chart-wrap {
    position: relative;
    height: 180px;
  }

  canvas { width: 100% !important; }

  /* BOTTOM GRID */
  .bottom-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  /* RECENT EVENTS */
  .event-list { display: flex; flex-direction: column; gap: 2px; }

  .event-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 14px;
    border-radius: 9px;
    transition: background 0.12s;
    cursor: pointer;
  }

  .event-item:hover { background: #252525; }

  .event-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .event-dot.red { background: var(--accent); box-shadow: 0 0 5px var(--accent); }
  .event-dot.yellow { background: var(--yellow); box-shadow: 0 0 5px var(--yellow); }
  .event-dot.green { background: var(--green); box-shadow: 0 0 5px var(--green); }
  .event-dot.blue { background: var(--blue); box-shadow: 0 0 5px var(--blue); }

  .event-content { flex: 1; min-width: 0; }

  .event-title {
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .event-sub {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 1px;
  }

  .event-time {
    font-size: 11px;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  /* QUICK SETTINGS */
  .quick-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 14px;
  }

  .quick-btn {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 10px;
    padding: 14px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    cursor: pointer;
    font-size: 12px;
    color: var(--text-primary);
    transition: all 0.15s;
  }

  .quick-btn:hover { background: #1a1a1a; border-color: #2a2a2a; }
  .quick-btn svg { width: 18px; height: 18px; color: var(--text-secondary); }

  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 4px;
    border-bottom: 1px solid #141414;
  }

  .toggle-row:last-child { border-bottom: none; }

  .toggle-label { font-size: 13px; font-weight: 600; }
  .toggle-sub { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }

  .toggle {
    width: 40px; height: 22px;
    border-radius: 11px;
    border: none;
    cursor: pointer;
    position: relative;
    transition: background 0.2s;
    flex-shrink: 0;
  }

  .toggle.off { background: #2a2a2a; }
  .toggle.on { background: #ffffff; }

  .toggle::after {
    content: '';
    width: 16px; height: 16px;
    border-radius: 50%;
    position: absolute;
    top: 3px;
    transition: left 0.2s;
  }

  .toggle.off::after { left: 3px; background: #666; }
  .toggle.on::after { left: 21px; background: #000; }

  /* HAMBURGER */
  .hamburger {
    display: none;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
    padding: 6px;
  }

  .hamburger span {
    display: block;
    width: 20px; height: 2px;
    background: var(--text-secondary);
    border-radius: 2px;
    transition: all 0.2s;
  }

  .sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 40;
  }

  /* MOBILE */
  @media (max-width: 900px) {
    :root { --sidebar-width: 0px; }

    aside {
      width: 200px;
      transform: translateX(-100%);
    }

    aside.open { transform: translateX(0); }

    .sidebar-overlay.show { display: block; }

    main { margin-left: 0; padding: 20px 16px; }

    .hamburger { display: flex; }

    .stat-grid { grid-template-columns: repeat(2, 1fr); }

    .bottom-grid { grid-template-columns: 1fr; }

    .stat-value { font-size: 26px; }
  }

  @media (max-width: 480px) {
    .stat-grid { grid-template-columns: 1fr; }
    main { padding: 16px 12px; }
    .page-title { font-size: 17px; }
  }
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="hamburger" id="hamburger">
      <span></span><span></span><span></span>
    </div>
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      </div>
      RobloxStore
    </div>
  </div>
  <div class="header-right">
    <div class="status-dot"></div>
    <button class="header-btn" title="새로고침">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
    </button>
    <button class="header-btn" title="라이트 모드">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
    </button>
  </div>
</header>

<div class="sidebar-overlay" id="overlay"></div>

<div class="layout">

  <!-- SIDEBAR -->
  <aside id="sidebar">
    <div class="nav-section-label">메인</div>
    <a class="nav-item active" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      대시보드
    </a>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>
      상품 관리
    </a>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      주문 목록
    </a>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2a10 10 0 100 20A10 10 0 0012 2z"/><path d="M12 8v4l3 3"/></svg>
      거래 내역
    </a>

    <div class="nav-section-label">관리</div>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
      구매자 관리
    </a>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 8h1a4 4 0 010 8h-1"/><path d="M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>
      쿠폰 관리
    </a>

    <div class="nav-section-label">로그</div>
    <a class="nav-item" href="#">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
      판매 로그
    </a>

    <div class="nav-bottom">
      <a class="nav-item" href="#">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/></svg>
        라이트 모드
      </a>
      <a class="nav-item danger" href="#">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        로그아웃
      </a>
    </div>
  </aside>

  <!-- MAIN CONTENT -->
  <main>
    <div class="page-title">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      대시보드
    </div>
    <p class="page-subtitle">RobloxStore 판매 현황 및 빠른 설정</p>

    <!-- STAT CARDS -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          오늘 판매
        </div>
        <div class="stat-value">3,512</div>
        <div class="stat-change">+24% 어제 대비</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          주간 판매
        </div>
        <div class="stat-value">18,740</div>
        <div class="stat-change">+12% 지난 주 대비</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          월간 판매
        </div>
        <div class="stat-value">74,320</div>
        <div class="stat-change">+8% 지난 달 대비</div>
      </div>
    </div>

    <!-- CHART -->
    <div class="chart-card">
      <div class="card-header">
        <div class="card-title">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          판매 추이
        </div>
        <select class="period-select">
          <option>주</option>
          <option>월</option>
          <option>연</option>
        </select>
      </div>
      <div class="chart-wrap">
        <canvas id="salesChart"></canvas>
      </div>
    </div>

    <!-- BOTTOM -->
    <div class="bottom-grid">
      <!-- RECENT EVENTS -->
      <div class="chart-card" style="margin-bottom:0;">
        <div class="card-header">
          <div class="card-title">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            최근 이벤트
          </div>
        </div>
        <div class="event-list">
          <div class="event-item">
            <div class="event-dot red"></div>
            <div class="event-content">
              <div class="event-title">신규 주문 — #sword-pack-001</div>
              <div class="event-sub">Gaming Zone · user#4821</div>
            </div>
            <div class="event-time">방금</div>
          </div>
          <div class="event-item">
            <div class="event-dot yellow"></div>
            <div class="event-content">
              <div class="event-title">결제 대기 — VIP 패스</div>
              <div class="event-sub">Anime Hub · user#3392</div>
            </div>
            <div class="event-time">3분</div>
          </div>
          <div class="event-item">
            <div class="event-dot green"></div>
            <div class="event-content">
              <div class="event-title">자동 배송 완료</div>
              <div class="event-sub">Dev Community · 신규 구매자</div>
            </div>
            <div class="event-time">11분</div>
          </div>
          <div class="event-item">
            <div class="event-dot red"></div>
            <div class="event-content">
              <div class="event-title">사기 의심 결제 감지</div>
              <div class="event-sub">Anime Hub · fakepay.xyz</div>
            </div>
            <div class="event-time">28분</div>
          </div>
          <div class="event-item">
            <div class="event-dot blue"></div>
            <div class="event-content">
              <div class="event-title">가격 정책 업데이트</div>
              <div class="event-sub">할인율 변경 5% → 3%</div>
            </div>
            <div class="event-time">1시간</div>
          </div>
        </div>
      </div>

      <!-- QUICK SETTINGS -->
      <div class="chart-card" style="margin-bottom:0;">
        <div class="card-header">
          <div class="card-title">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/></svg>
            빠른 설정
          </div>
        </div>

        <div class="quick-grid">
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>
            상품 추가
          </button>
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            주문 조회
          </button>
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
            결제 관리
          </button>
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>
            키워드 필터
          </button>
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            사기 감지
          </button>
          <button class="quick-btn">
            <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
            구매자 인증
          </button>
        </div>

        <div class="toggle-row">
          <div>
            <div class="toggle-label">판매 일시정지</div>
            <div class="toggle-sub">즉시 판매 중단</div>
          </div>
          <button class="toggle off" onclick="this.classList.toggle('on');this.classList.toggle('off')"></button>
        </div>
        <div class="toggle-row">
          <div>
            <div class="toggle-label">주문 알림 DM</div>
            <div class="toggle-sub">구매자에게 자동 DM 발송</div>
          </div>
          <button class="toggle on" onclick="this.classList.toggle('on');this.classList.toggle('off')"></button>
        </div>
        <div class="toggle-row">
          <div>
            <div class="toggle-label">관리자 알림</div>
            <div class="toggle-sub">이벤트 발생 시 채널 공지</div>
          </div>
          <button class="toggle on" onclick="this.classList.toggle('on');this.classList.toggle('off')"></button>
        </div>
      </div>
    </div>
  </main>
</div>

<script>
  // Sidebar toggle
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const hamburger = document.getElementById('hamburger');

  hamburger.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  });

  overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  });

  // Chart
  const canvas = document.getElementById('salesChart');
  const ctx = canvas.getContext('2d');

  function drawChart() {
    const W = canvas.parentElement.clientWidth;
    const H = 180;
    canvas.width = W * devicePixelRatio;
    canvas.height = H * devicePixelRatio;
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);

    const data = [420, 280, 520, 260, 680, 740, 490];
    const labels = ['월', '화', '수', '목', '금', '토', '일'];
    const pad = { l: 40, r: 20, t: 10, b: 30 };
    const cW = W - pad.l - pad.r;
    const cH = H - pad.t - pad.b;
    const minV = 200, maxV = 800;

    const x = (i) => pad.l + (i / (data.length - 1)) * cW;
    const y = (v) => pad.t + cH - ((v - minV) / (maxV - minV)) * cH;

    // Grid lines
    ctx.strokeStyle = '#161616';
    ctx.lineWidth = 1;
    [250, 350, 450, 550, 650, 750].forEach(v => {
      ctx.beginPath();
      ctx.moveTo(pad.l, y(v));
      ctx.lineTo(W - pad.r, y(v));
      ctx.stroke();
    });

    // Y labels
    ctx.fillStyle = '#444';
    ctx.font = '10px Segoe UI, sans-serif';
    ctx.textAlign = 'right';
    [250, 350, 450, 550, 650, 750].forEach(v => {
      ctx.fillText(v, pad.l - 6, y(v) + 4);
    });

    // X labels
    ctx.textAlign = 'center';
    labels.forEach((l, i) => {
      ctx.fillText(l, x(i), H - 6);
    });

    // Area fill
    const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + cH);
    grad.addColorStop(0, 'rgba(255,255,255,0.12)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.beginPath();
    ctx.moveTo(x(0), y(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx = (x(i - 1) + x(i)) / 2;
      ctx.bezierCurveTo(cx, y(data[i - 1]), cx, y(data[i]), x(i), y(data[i]));
    }
    ctx.lineTo(x(data.length - 1), pad.t + cH);
    ctx.lineTo(x(0), pad.t + cH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(x(0), y(data[0]));
    for (let i = 1; i < data.length; i++) {
      const cx = (x(i - 1) + x(i)) / 2;
      ctx.bezierCurveTo(cx, y(data[i - 1]), cx, y(data[i]), x(i), y(data[i]));
    }
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots
    data.forEach((v, i) => {
      ctx.beginPath();
      ctx.arc(x(i), y(v), 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }

  drawChart();
  window.addEventListener('resize', drawChart);
</script>
</body>
</html>
