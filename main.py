<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
<style>
  *, *::before, *::after {
    margin: 0; padding: 0; box-sizing: border-box;
  }

  :root {
    --bg: #000;
    --surface: #0a0a0a;
    --surface2: #111;
    --border: #1e1e1e;
    --border2: #2a2a2a;
    --text: #fff;
    --muted: #666;
    --muted2: #444;
    --green: #3ecf7a;
    --red: #ff4d4d;
    --nav-h: 54px;
    --font: 'DM Sans', sans-serif;
    --mono: 'DM Mono', monospace;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 14px;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  nav {
    height: var(--nav-h);
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    position: sticky;
    top: 0;
    z-index: 100;
    gap: 16px;
  }

  .nav-left {
    display: flex;
    align-items: center;
    gap: 28px;
  }

  .brand {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.4px;
    white-space: nowrap;
    color: var(--text);
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 500;
    color: var(--muted);
    text-decoration: none;
    transition: all 0.15s;
    white-space: nowrap;
  }

  .nav-link:hover {
    color: var(--text);
    background: var(--surface2);
  }

  .nav-link.active {
    color: var(--text);
    border-bottom: 2px solid var(--text);
    border-radius: 0;
    padding-bottom: 4px;
  }

  .nav-link svg {
    width: 13px;
    height: 13px;
    flex-shrink: 0;
  }

  .nav-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .nav-pill {
    display: flex;
    align-items: center;
    gap: 7px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s;
  }

  .nav-pill:hover {
    background: var(--surface2);
  }

  .nav-pill .dot {
    width: 7px;
    height: 7px;
    background: var(--green);
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 5px var(--green);
  }

  .hamburger {
    display: none;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
    padding: 4px;
    background: none;
    border: none;
  }

  .hamburger span {
    display: block;
    width: 18px;
    height: 2px;
    background: var(--muted);
    border-radius: 2px;
  }

  .page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 24px;
  }

  .welcome {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }

  .welcome-text h1 {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
  }

  .welcome-text p {
    color: var(--muted);
    font-size: 13px;
  }

  .welcome-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    color: var(--muted);
    cursor: text;
    min-width: 160px;
  }

  .search-box svg {
    width: 13px;
    height: 13px;
    flex-shrink: 0;
  }

  .btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--font);
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    transition: all 0.15s;
    white-space: nowrap;
  }

  .btn:hover {
    background: var(--surface2);
    border-color: var(--border2);
  }

  .btn svg {
    width: 12px;
    height: 12px;
  }

  .btn-primary {
    background: var(--text);
    color: #000;
    border-color: var(--text);
  }

  .btn-primary:hover {
    background: #e0e0e0;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
  }

  .stat-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .stat-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 500;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .stat-label svg { width: 12px; height: 12px; }
  .stat-label .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .dot-green { background: var(--green); }
  .dot-white { background: #fff; }

  .stat-badge {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 11px;
    font-weight: 600;
    color: var(--green);
    font-family: var(--mono);
  }
  .stat-badge svg { width: 10px; height: 10px; }

  .stat-value {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1;
    margin-bottom: 2px;
  }

  .stat-sub {
    font-size: 11px;
    color: var(--muted);
  }

  .chart-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 24px;
  }

  .chart-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 6px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .chart-head-left h3 {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 3px;
  }

  .chart-head-left p {
    font-size: 12px;
    color: var(--muted);
  }

  .chart-head-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--muted);
  }

  .legend-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .chart-wrap {
    position: relative;
    height: 260px;
    margin: 16px 0 0;
  }

  canvas {
    display: block;
  }

  .chart-tooltip {
    position: absolute;
    background: #fff;
    color: #000;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 6px;
    pointer-events: none;
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.15s;
    transform: translate(-50%, -100%);
    margin-top: -8px;
    z-index: 10;
    font-family: var(--mono);
  }

  .chart-tooltip.visible {
    opacity: 1;
  }

  .deals-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .deal-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }

  .deal-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px 14px;
    border-bottom: 1px solid var(--border);
  }

  .deal-card-title {
    font-size: 14px;
    font-weight: 700;
  }

  .deal-card-title span {
    font-weight: 400;
    color: var(--muted);
    margin-left: 5px;
    font-size: 13px;
  }

  .deal-table {
    width: 100%;
    border-collapse: collapse;
  }

  .deal-table th {
    font-size: 10px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 8px 20px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }

  .deal-table td {
    padding: 11px 20px;
    font-size: 13px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }

  .deal-table tr:last-child td {
    border-bottom: none;
  }

  .deal-table tr:hover td {
    background: #0d0d0d;
  }

  .user-cell {
    display: flex;
    align-items: center;
    gap: -4px;
  }

  .avatar {
    width: 24px;
    height: 24px;
    background: var(--surface2);
    border: 2px solid var(--border2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    font-weight: 700;
    margin-right: -6px;
    position: relative;
  }

  .avatar:first-child {
    z-index: 2;
  }

  .avatar:last-child {
    margin-right: 8px;
    z-index: 1;
  }

  .coin-badge {
    display: flex;
    align-items: center;
    gap: 5px;
    background: #0d0d0d;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 500;
    font-family: var(--mono);
  }

  .coin-dot {
    width: 6px;
    height: 6px;
    background: #fff;
    border-radius: 50%;
  }

  .amount {
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 500;
  }

  .actions-cell {
    display: flex;
    gap: 4px;
  }

  .action-dot {
    width: 4px;
    height: 4px;
    background: var(--muted2);
    border-radius: 50%;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
  }

  .status-open {
    background: rgba(255,255,255,0.07);
    color: #fff;
  }

  .status-closed {
    background: rgba(62,207,122,0.12);
    color: var(--green);
  }

  .add-deal {
    padding: 12px 20px;
    text-align: center;
    font-size: 12px;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }

  .add-deal a {
    color: var(--text);
    text-decoration: none;
    font-weight: 600;
  }

  .add-deal a:hover {
    text-decoration: underline;
  }

  .mobile-menu {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 200;
  }

  .mobile-menu.open {
    display: block;
  }

  .mm-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0,0,0,0.7);
  }

  .mm-panel {
    position: absolute;
    top: 0;
    left: 0;
    width: 230px;
    height: 100%;
    background: #060606;
    border-right: 1px solid var(--border);
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .mobile-menu.open .mm-panel {
    transform: translateX(0);
  }

  .mm-link {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 12px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: var(--muted);
    text-decoration: none;
    transition: all 0.12s;
  }

  .mm-link:hover,
  .mm-link.active {
    background: var(--surface2);
    color: var(--text);
  }

  .mm-link svg {
    width: 15px;
    height: 15px;
  }

  @media (max-width: 1100px) {
      .stat-grid {
          grid-template-columns: repeat(2, 1fr);
      }
  }

  @media (max-width: 860px) {
      .deals-grid {
          grid-template-columns: 1fr;
      }
      .nav-links {
          display: none;
      }
      .hamburger {
          display: flex;
      }
      .search-box {
          display: none;
      }
  }

  @media (max-width: 600px) {
      .page {
          padding: 20px 14px;
      }
      nav {
          padding: 0 16px;
      }
      .stat-grid {
          grid-template-columns: 1fr 1fr;
          gap: 10px;
      }
      .stat-value {
          font-size: 24px;
      }
      .welcome-actions {
          width: 100%;
      }
      .welcome-text h1 {
          font-size: 19px;
      }
      .deal-table th:nth-child(3),
      .deal-table td:nth-child(3) {
          display: none;
      }
  }
  @media (max-width: 400px) {
      .stat-grid {
          grid-template-columns: 1fr;
      }
  }
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-left">
    <button class="hamburger" id="hamburger" aria-label="메뉴 열기">
      <span></span><span></span><span></span>
    </button>
    <div class="brand"> {/* 브랜드명 그대로 유지 가능, 삭제 원하면 알려주세요 */}RobloxStore</div>
    <div class="nav-links">
      <a href="#" class="nav-link active" aria-current="page">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
        대시보드
      </a>
      <a href="#" class="nav-link">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
          <line x1="3" y1="6" x2="21" y2="6" />
          <path d="M16 10a4 4 0 01-8 0" />
        </svg>
        상품
      </a>
      <a href="#" class="nav-link">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        주문
      </a>
      <a href="#" class="nav-link">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </svg>
        지원
      </a>
    </div>
  </div>
  <div class="nav-right">
    <div class="nav-pill" tabindex="0" role="button">
      <div class="dot"></div>
      관리자
    </div>
    <button class="btn btn-primary" type="button" style="padding:6px 14px;font-size:12px;">
      <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <line x1="12" y1="5" x2="12" y2="19" />
        <line x1="5" y1="12" x2="19" y2="12" />
      </svg>
      상품 추가
    </button>
  </div>
</nav>

<!-- MOBILE MENU -->
<div class="mobile-menu" id="mobileMenu" aria-hidden="true">
  <div class="mm-overlay" id="mmOverlay" tabindex="0"></div>
  <div class="mm-panel">
    <div style="font-size:15px;font-weight:700;padding:4px 12px 16px;border-bottom:1px solid var(--border);margin-bottom:8px;">RobloxStore</div>
    <a href="#" class="mm-link active" aria-current="page">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
      </svg>
      대시보드
    </a>
    <a href="#" class="mm-link">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <path d="M16 10a4 4 0 01-8 0" />
      </svg>
      상품 관리
    </a>
    <a href="#" class="mm-link">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <line x1="8" y1="6" x2="21" y2="6" />
        <line x1="8" y1="12" x2="21" y2="12" />
        <line x1="8" y1="18" x2="21" y2="18" />
        <line x1="3" y1="6" x2="3.01" y2="6" />
        <line x1="3" y1="12" x2="3.01" y2="12" />
        <line x1="3" y1="18" x2="3.01" y2="18" />
      </svg>
      주문 목록
    </a>
    <a href="#" class="mm-link">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
        <circle cx="9" cy="7" r="4" />
      </svg>
      구매자 관리
    </a>
    <a href="#" class="mm-link">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
      판매 로그
    </a>
    <div style="margin-top:auto;padding-top:16px;border-top:1px solid var(--border);">
      <a href="#" class="mm-link" style="color:#ff4d4d;">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
        로그아웃
      </a>
    </div>
  </div>
</div>

<!-- PAGE -->
<div class="page">

  <div class="welcome">
    <div class="welcome-text">
      <h1>안녕하세요, 관리자님</h1>
      <p>현재 판매 현황 및 최근 거래 내역을 확인하세요</p>
    </div>
    <div class="welcome-actions">
      <div class="search-box">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        검색...
      </div>
      <button class="btn" type="button">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        최근 7일
      </button>
    </div>
  </div>

  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-card-top">
        <div class="stat-label"><span class="dot dot-green"></span> 완료된 판매</div>
        <div class="stat-badge">
          <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <polyline points="18 15 12 9 6 15" />
          </svg>
          74.5%
        </div>
      </div>
      <div class="stat-value">2,664</div>
      <div class="stat-sub">총 판매 건수</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-top">
        <div class="stat-label"><span class="dot dot-white"></span> 총 판매 금액</div>
        <div class="stat-badge">
          <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <polyline points="18 15 12 9 6 15" />
          </svg>
          74.5%
        </div>
      </div>
      <div class="stat-value">₩14,899</div>
      <div class="stat-sub">이번 주 누적</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-top">
        <div class="stat-label"><span class="dot dot-white"></span> 평균 처리 시간</div>
        <div class="stat-badge">
          <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <polyline points="18 15 12 9 6 15" />
          </svg>
          74.5%
        </div>
      </div>
      <div class="stat-value">1.4<span style="font-size:16px;font-weight:400;color:var(--muted);margin-left:4px;">일</span></div>
      <div class="stat-sub">평균 배송 일수</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-top">
        <div class="stat-label"><span class="dot dot-green"></span> 진행 중</div>
        <div class="stat-badge">
          <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <polyline points="18 15 12 9 6 15" />
          </svg>
          74.5%
        </div>
      </div>
      <div class="stat-value">2,664</div>
      <div class="stat-sub">처리 중인 주문</div>
    </div>
  </div>

  <div class="chart-section">
    <div class="chart-head">
      <div class="chart-head-left">
        <h3>판매 완료 현황</h3>
        <p>현재 판매 추이 및 세부 내역</p>
      </div>
      <div class="chart-head-right">
        <div class="legend">
          <div class="legend-item"><div class="legend-dot" style="background:#fff;"></div> 완료 판매</div>
          <div class="legend-item"><div class="legend-dot" style="background:#3ecf7a;"></div> 평균 처리</div>
        </div>
        <button class="btn" type="button">
          <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          최근 7일
        </button>
      </div>
    </div>
    <div class="chart-wrap">
      <canvas id="chart"></canvas>
      <div id="tip" class="chart-tooltip"></div>
    </div>
  </div>

  <div class="deals-grid">

    <div class="deal-card">
      <div class="deal-card-head">
        <div class="deal-card-title">진행 중 주문 <span>(3)</span></div>
        <button class="btn" style="padding:5px 10px;font-size:11px;" type="button">전체 보기</button>
      </div>
      <table class="deal-table" role="grid">
        <thead>
          <tr>
            <th>구매자</th>
            <th>상품</th>
            <th>금액</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="KJ 유저">KJ</div>
                <div class="avatar" aria-label="MR 유저">MR</div>
                <span style="margin-left:10px;font-size:12px;">user#4821</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>소드팩</div></td>
            <td><span class="amount">₩8,500</span></td>
            <td><span class="status-badge status-open">진행</span></td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="YS 유저">YS</div>
                <div class="avatar" aria-label="PK 유저">PK</div>
                <span style="margin-left:10px;font-size:12px;">user#3392</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>VIP 패스</div></td>
            <td><span class="amount">₩15,000</span></td>
            <td><span class="status-badge status-open">진행</span></td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <div class="avatar" aria-label="TH 유저">TH</div>
                <div class="avatar" aria-label="LM 유저">LM</div>
                <span style="margin-left:10px;font-size:12px;">user#7701</span>
              </div>
            </td>
            <td><div class="coin-badge"><div class="coin-dot"></div>코인팩 x10</div></td>
            <td><span class="amount">₩5,200</span></td>
            <td><span class="status-badge status-open">진행</span></td>
          </tr>
        </tbody>
      </table>
      <div class="add-deal">다른 상품 등록? <a href="#">여기를 클릭</a></div>
    </div>

    <div class="deal-card">
      <div class="deal-card-head">
        <div class="deal-card-title">완료 주문 <span>(10)</span></div>
        <button class="btn" style="padding:5px 10px;font-size:11px;" type="button">전체 보기</button>
      </div>
      <table class="deal-table" role="grid">
        <thead>
          <tr>
            <th>구매자</th>
            <th>상품</th>
            <th>금액</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="AB 유저">AB</div><div class="avatar" aria-label="CD 유저">CD</div><span style="margin-left:10px;font-size:12px;">user#1012</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>소드팩</div></td>
            <td><span class="amount">₩8,500</span></td>
            <td><span class="status-badge status-closed">완료</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="EF 유저">EF</div><div class="avatar" aria-label="GH 유저">GH</div><span style="margin-left:10px;font-size:12px;">user#2234</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>VIP 패스</div></td>
            <td><span class="amount">₩15,000</span></td>
            <td><span class="status-badge status-closed">완료</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="IJ 유저">IJ</div><div class="avatar" aria-label="KL 유저">KL</div><span style="margin-left:10px;font-size:12px;">user#3358</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>코인팩 x5</div></td>
            <td><span class="amount">₩2,900</span></td>
            <td><span class="status-badge status-closed">완료</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="MN 유저">MN</div><div class="avatar" aria-label="OP 유저">OP</div><span style="margin-left:10px;font-size:12px;">user#4490</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>스킨팩</div></td>
            <td><span class="amount">₩11,200</span></td>
            <td><span class="status-badge status-closed">완료</span></td>
          </tr>
          <tr>
            <td><div class="user-cell"><div class="avatar" aria-label="QR 유저">QR</div><div class="avatar" aria-label="ST 유저">ST</div><span style="margin-left:10px;font-size:12px;">user#5512</span></div></td>
            <td><div class="coin-badge"><div class="coin-dot"></div>소드팩</div></td>
            <td><span class="amount">₩8,500</span></td>
            <td><span class="status-badge status-closed">완료</span></td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</div>

<script>
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');
  const mmOverlay = document.getElementById('mmOverlay');

  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
    mobileMenu.setAttribute('aria-hidden', mobileMenu.classList.contains('open') ? 'false' : 'true');
  });

  mmOverlay.addEventListener('click', () => {
    mobileMenu.classList.remove('open');
    mobileMenu.setAttribute('aria-hidden', 'true');
  });

  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const tip = document.getElementById('tip');

  const sales = [12, 18, 22, 45, 58, 72, 80];
  const avg = [3, 5, 7, 12, 15, 18, 20];
  const xlabels = ['2/5', '2/6', '2/7', '2/8', '2/9', '2/10', '2/11'];
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

    ctx.strokeStyle = '#181818';
    ctx.lineWidth = 1;
    [0, 20, 40, 60, 80].forEach(v => {
      const yy = PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH;
      ctx.beginPath();
      ctx.moveTo(PAD.l, yy);
      ctx.lineTo(CW - PAD.r, yy);
      ctx.stroke();
    });

    ctx.font = font;
    ctx.fillStyle = '#444';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    [0, 20, 40, 60, 80].forEach(v => {
      const yy = PAD.t + cH - ((v - MINS) / (MAXS - MINS)) * cH;
      ctx.fillText(v, PAD.l - 6, yy);
    });

    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = '#444';
    PXs.forEach((px, i) => ctx.fillText(xlabels[i], px, H - 8));

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

    drawArea(PYs, 'rgba(255,255,255,1)');
    drawArea(PYa, 'rgba(62,207,122,1)');
    drawLine(PYa, '#3ecf7a', 2);
    drawLine(PYs, '#ffffff', 2.5);

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
    tip.style.top = (ty - 8) + 'px';
    tip.textContent = `${xlabels[idx]}  판매 ${sales[idx]}건 / 처리 ${avg[idx]}건`;
    tip.classList.add('visible');
    if (!rafId) rafId = requestAnimationFrame(animTip);
    draw(idx);
  }

  function hideTip() {
    activeIdx = -1;
    tip.classList.remove('visible');
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
</script>

</body>
</html>
