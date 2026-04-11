<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light only">
<meta name="theme-color" content="#ffffff">
<title>SailorPiece</title>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html { background:#fff !important; color-scheme:light; }

:root {
  --blue: #0ea5e9;
  --blue-d: #0284c7;
  --text: #0f172a;
  --text2: #475569;
  --text3: #94a3b8;
  --border: rgba(14,165,233,0.12);
}

body {
  font-family: 'Pretendard', -apple-system, sans-serif;
  background: #fff !important;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  max-width: 680px;
  margin: 0 auto;
}

/* NAV */
nav {
  position: fixed; top:0; left:50%; transform:translateX(-50%);
  width: 100%; max-width: 680px;
  height: 52px; z-index: 100;
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px;
}

.logo { font-size: 16px; font-weight: 700; color: var(--blue); letter-spacing: -0.3px; }

.nav-r { display: flex; gap: 8px; }

.nav-btn {
  height: 34px; padding: 0 14px;
  border-radius: 999px; font-size: 13px; font-weight: 500;
  cursor: pointer; border: 1px solid var(--border);
  background: rgba(255,255,255,0.8);
  color: var(--text2); transition: all .15s;
  display: inline-flex; align-items: center; gap: 6px;
}
.nav-btn:hover { color: var(--blue); }
.nav-btn.pri {
  background: rgba(14,165,233,0.09);
  color: var(--blue); font-weight: 600;
  border-color: rgba(14,165,233,0.2);
}
.cart-badge {
  background: var(--blue); color: #fff;
  border-radius: 999px; width: 16px; height: 16px;
  font-size: 9px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

/* PAGE */
.page { display:none; }
.page.on { display:block; }

/* HERO */
.hero {
  padding: 80px 20px 24px;
  background: linear-gradient(170deg, #f0f9ff 0%, #fff 65%);
  text-align: center;
}

.eyebrow {
  font-size: 10px; font-weight: 600;
  letter-spacing: 1.4px; text-transform: uppercase;
  color: var(--blue); margin-bottom: 8px;
  opacity:0; animation: up .5s .05s forwards;
}

.hero h1 {
  font-size: 38px; font-weight: 700;
  letter-spacing: -1.5px; line-height: 1.1;
  color: var(--text); margin-bottom: 0;
  opacity:0; animation: up .5s .13s forwards;
}
.hero h1 em { font-style:normal; color: var(--blue); }

.hero-btns {
  display: flex; gap: 10px; justify-content: center;
  margin-top: 14px; margin-bottom: 14px;
  opacity:0; animation: up .5s .21s forwards;
}

.btn-fill {
  height: 40px; padding: 0 20px;
  border-radius: 999px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: none;
  background: var(--blue); color: #fff;
  box-shadow: 0 4px 14px rgba(14,165,233,0.3);
  display: inline-flex; align-items: center; gap: 7px;
  transition: all .15s;
}
.btn-fill:hover { background: var(--blue-d); }

.btn-ghost {
  height: 40px; padding: 0 20px;
  border-radius: 999px; font-size: 13px; font-weight: 500;
  cursor: pointer;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  color: var(--blue);
  display: inline-flex; align-items: center; gap: 7px;
  transition: all .15s;
}
.btn-ghost:hover { background: #fff; }

/* STATS */
.stats-bar {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(14,165,233,0.08), inset 0 1px 0 rgba(255,255,255,0.9);
  padding: 0;
  opacity:0; animation: up .5s .29s forwards;
  overflow: hidden;
}
.s-item {
  flex: 1; text-align: center;
  padding: 14px 8px;
  border-right: 1px solid rgba(14,165,233,0.1);
}
.s-item:last-child { border-right: none; }
.s-n { font-size: 18px; font-weight: 700; color: var(--blue); letter-spacing: -0.5px; }
.s-l { font-size: 10px; color: var(--text3); margin-top: 2px; font-weight: 500; }

/* DIVIDER */
.divider { height: 1px; background: rgba(14,165,233,0.1); margin: 16px 20px 0; }

/* SHOP */
.shop { padding: 16px 20px; }

.shop-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.shop-title { font-size: 16px; font-weight: 700; letter-spacing: -0.3px; }

.sort-sel {
  height: 32px; padding: 0 12px;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border); border-radius: 999px;
  font-size: 12px; color: var(--text2); outline: none; cursor: pointer;
}

/* GRID */
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.card {
  background: #fff;
  border: 1px solid rgba(14,165,233,0.1);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 2px 12px rgba(14,165,233,0.06);
  transition: transform .18s, box-shadow .18s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(14,165,233,0.12); }

.card-img {
  width: 100%; aspect-ratio: 1;
  background: #f8fbff;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  border-bottom: 1px solid rgba(14,165,233,0.06);
}
.card-icon {
  width: 52px; height: 52px;
  background: rgba(255,255,255,0.8);
  border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(14,165,233,0.1);
}
.card-icon svg { width: 26px; height: 26px; color: var(--blue); stroke-width: 1.7; }

.card-tag {
  position: absolute; top: 8px; left: 8px;
  font-size: 9px; font-weight: 700;
  padding: 3px 8px; border-radius: 999px;
}
.hot    { background: rgba(254,243,199,0.95); color: #d97706; }
.rare   { background: rgba(237,233,254,0.95); color: #7c3aed; }
.new    { background: rgba(209,250,229,0.95); color: #059669; }
.legend { background: rgba(254,226,226,0.95); color: #dc2626; }

.card-body { padding: 12px; background: #fff; }
.card-name { font-size: 14px; font-weight: 700; margin-bottom: 3px; letter-spacing: -0.2px; }
.card-desc { font-size: 11px; color: var(--text3); margin-bottom: 10px; line-height: 1.4; }
.card-foot { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.card-price { font-size: 15px; font-weight: 700; color: var(--blue); }
.card-price small { font-size: 9px; color: var(--text3); font-weight: 400; }

.add-btn {
  height: 30px; padding: 0 13px;
  background: rgba(14,165,233,0.1);
  border: 1px solid rgba(14,165,233,0.2);
  border-radius: 999px; font-size: 11px; font-weight: 700;
  color: var(--blue); cursor: pointer; transition: all .13s;
}
.add-btn:hover { background: rgba(14,165,233,0.2); }
.add-btn:active { transform: scale(0.95); }

.card-stock { font-size: 10px; color: #f87171; font-weight: 600; margin-top: 6px; }

/* BOT */
.bot {
  background: linear-gradient(150deg, #f0f9ff 0%, #fff 60%);
  border-top: 1px solid var(--border);
  padding: 36px 20px;
}
.bot h2 { font-size: 22px; font-weight: 700; letter-spacing: -0.7px; margin-bottom: 8px; }
.bot p { font-size: 13px; color: var(--text2); line-height: 1.7; margin-bottom: 16px; }

.cmd-list { display: flex; flex-direction: column; gap: 6px; }
.cmd {
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.9);
  border-radius: 11px; padding: 10px 14px;
  display: flex; justify-content: space-between; align-items: center;
}
.cmd-k { font-family: 'SF Mono', Monaco, monospace; font-size: 12px; font-weight: 700; color: var(--blue); }
.cmd-v { font-size: 11px; color: var(--text3); }

/* FOOTER */
footer {
  border-top: 1px solid var(--border);
  padding: 16px 20px;
  display: flex; justify-content: space-between; align-items: center;
}
footer p { font-size: 11px; color: var(--text3); }
.foot-links { display: flex; gap: 14px; }
.foot-links span { font-size: 11px; color: var(--text3); cursor: pointer; }
.foot-links span:hover { color: var(--blue); }

/* INNER */
.inner { max-width: 680px; margin: 62px auto 0; padding: 28px 20px; }
.pg-title { font-size: 20px; font-weight: 700; letter-spacing: -0.4px; margin-bottom: 4px; }
.pg-sub { font-size: 13px; color: var(--text2); margin-bottom: 20px; }
.row { display: flex; gap: 8px; margin-bottom: 18px; }
.inp {
  flex:1; max-width:220px; height:38px; padding:0 14px;
  border:1px solid var(--border); border-radius:999px;
  font-size:13px; color:var(--text);
  background:rgba(255,255,255,0.8); outline:none;
}
.inp:focus { border-color:var(--blue); }
.inp::placeholder { color:var(--text3); }

/* TABLE */
.tbl-wrap {
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 14px; overflow: hidden;
  box-shadow: 0 2px 14px rgba(14,165,233,0.06);
  margin-bottom: 22px;
}
table { width:100%; border-collapse:collapse; }
th { background:rgba(224,242,254,0.5); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.6px; color:var(--text3); padding:10px 14px; text-align:left; border-bottom:1px solid var(--border); }
td { padding:11px 14px; font-size:12px; color:var(--text2); border-bottom:1px solid var(--border); }
tr:last-child td { border-bottom:none; }

.st { display:inline-flex; align-items:center; gap:4px; padding:3px 9px; border-radius:999px; font-size:10px; font-weight:600; }
.st::before { content:''; width:5px; height:5px; border-radius:50%; }
.st-p  { background:#fef9c3; color:#a16207; } .st-p::before  { background:#eab308; }
.st-ok { background:#d1fae5; color:#065f46; } .st-ok::before { background:#10b981; }
.st-no { background:#fee2e2; color:#991b1b; } .st-no::before { background:#ef4444; }

/* ADMIN */
.a-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-bottom:20px; }
.a-card { background:rgba(255,255,255,0.6); backdrop-filter:blur(16px); border:1px solid rgba(255,255,255,0.95); border-radius:14px; padding:14px; box-shadow:0 2px 12px rgba(14,165,233,0.05); }
.a-lbl { font-size:10px; color:var(--text3); font-weight:500; margin-bottom:5px; }
.a-val { font-size:22px; font-weight:700; color:var(--blue); letter-spacing:-0.5px; }
.sec-t { font-size:13px; font-weight:700; margin-bottom:10px; }

/* CART */
.cart-ov { display:none; position:fixed; inset:0; background:rgba(186,230,253,0.2); z-index:200; justify-content:flex-end; backdrop-filter:blur(6px); }
.cart-ov.on { display:flex; }
.drawer {
  background:rgba(255,255,255,0.88); backdrop-filter:blur(28px) saturate(180%);
  border-left:1px solid rgba(255,255,255,0.9);
  width:300px; height:100%; padding:22px;
  display:flex; flex-direction:column;
  animation:slide .22s ease;
  box-shadow:-4px 0 24px rgba(14,165,233,0.08);
}
@keyframes slide { from{transform:translateX(100%)} to{transform:translateX(0)} }
.d-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
.d-head h2 { font-size:15px; font-weight:700; }
.cls {
  width:26px; height:26px; border-radius:50%;
  background:rgba(14,165,233,0.08); border:1px solid rgba(14,165,233,0.14);
  color:var(--blue); font-size:12px; font-weight:700;
  cursor:pointer; display:flex; align-items:center; justify-content:center;
}
.d-body { flex:1; overflow-y:auto; }
.ci { display:flex; gap:9px; padding:10px 0; border-bottom:1px solid var(--border); align-items:center; }
.ci-ic { width:36px; height:36px; flex-shrink:0; background:rgba(224,242,254,0.8); border-radius:9px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(255,255,255,0.9); }
.ci-ic svg { width:17px; height:17px; color:var(--blue); stroke-width:1.7; }
.ci-nm { font-size:12px; font-weight:600; }
.ci-pr { font-size:11px; color:var(--text3); margin-top:1px; }
.ci-rm { background:none; border:none; color:var(--text3); cursor:pointer; font-size:13px; margin-left:auto; }
.ci-rm:hover { color:#f87171; }
.d-foot { padding-top:13px; border-top:1px solid var(--border); margin-top:10px; }
.d-tot { display:flex; justify-content:space-between; font-size:14px; font-weight:700; margin-bottom:11px; }
.ord-btn {
  width:100%; height:42px; background:#5865F2; color:#fff; border:none;
  border-radius:999px; font-size:13px; font-weight:700;
  cursor:pointer; display:flex; align-items:center; justify-content:center; gap:7px;
  box-shadow:0 4px 14px rgba(88,101,242,0.28); transition:opacity .15s;
}
.ord-btn:hover { opacity:.88; }
.d-note { text-align:center; font-size:10px; color:var(--text3); margin-top:7px; }
.empty { text-align:center; padding:36px 0; }
.empty p { font-size:12px; color:var(--text3); margin-top:8px; }

/* NAV TABS (PC) */
.nav-tabs-pc {
  display: flex; gap: 2px;
  background: rgba(14,165,233,0.07);
  border: 1px solid var(--border);
  border-radius: 999px; padding: 3px;
}
.ntab {
  padding: 5px 14px; border-radius: 999px;
  font-size: 12px; font-weight: 500; color: var(--text2);
  cursor: pointer; border: none; background: transparent; transition: all .15s;
}
.ntab:hover { color: var(--blue); }
.ntab.on { background: #fff; color: var(--blue); font-weight: 600; box-shadow: 0 1px 6px rgba(14,165,233,0.13); }

/* MODAL */
.m-ov { display:none; position:fixed; inset:0; background:rgba(186,230,253,0.2); z-index:300; align-items:center; justify-content:center; backdrop-filter:blur(10px); }
.m-ov.on { display:flex; }
.modal { background:rgba(255,255,255,0.9); backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.95); border-radius:18px; padding:26px; width:300px; box-shadow:0 16px 40px rgba(14,165,233,0.1); animation:up .2s ease; }
.modal h2 { font-size:16px; font-weight:700; margin-bottom:4px; }
.modal p { font-size:12px; color:var(--text2); margin-bottom:14px; }
.pw-inp { width:100%; height:38px; padding:0 13px; border:1px solid var(--border); border-radius:9px; font-size:13px; color:var(--text); background:rgba(255,255,255,0.8); outline:none; margin-bottom:12px; }
.pw-inp:focus { border-color:var(--blue); }
.m-btns { display:flex; gap:7px; }
.m-no { flex:1; height:36px; border-radius:999px; background:rgba(14,165,233,0.07); border:1px solid var(--border); font-size:12px; font-weight:600; color:var(--text2); cursor:pointer; }
.m-ok { flex:1; height:36px; border-radius:999px; background:var(--blue); border:none; font-size:12px; font-weight:600; color:#fff; cursor:pointer; }
.m-ok:hover { background:var(--blue-d); }

/* TOAST */
.toast { position:fixed; bottom:22px; left:50%; transform:translateX(-50%) translateY(50px); background:rgba(255,255,255,0.9); backdrop-filter:blur(16px); border:1px solid var(--border); color:var(--text); border-radius:999px; padding:9px 18px; font-size:12px; font-weight:500; z-index:999; transition:transform .22s ease; box-shadow:0 4px 16px rgba(14,165,233,0.1); white-space:nowrap; }
.toast.on { transform:translateX(-50%) translateY(0); }

@keyframes up { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="logo">SailorPiece</div>
  <div class="nav-tabs-pc">
    <button class="ntab on" onclick="goTab('shop',this)">쇼핑몰</button>
    <button class="ntab" onclick="goTab('orders',this)">주문 조회</button>
    <button class="ntab" onclick="openAdmin()">관리자</button>
  </div>
  <div class="nav-r">
    <button class="nav-btn" onclick="toast('디스코드 서버로 이동합니다.')">
      <svg width="13" height="10" viewBox="0 0 16 12" fill="var(--blue)"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
      디스코드
    </button>
    <button class="nav-btn pri" onclick="openCart()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2.2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      장바구니 <div class="cart-badge" id="cart-count">0</div>
    </button>
  </div>
</nav>

<!-- 쇼핑몰 -->
<div id="pg-shop" class="page on">
  <section class="hero">
    <div class="eyebrow">Sailor Piece — Official Item Store</div>
    <h1>세일러 피스<br><em>아이템 스토어</em></h1>
    <div class="hero-btns">
      <button class="btn-fill" onclick="document.getElementById('shop-sec').scrollIntoView({behavior:'smooth'})">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
        아이템 보기
      </button>
      <button class="btn-ghost" onclick="toast('초대 링크가 복사되었습니다.')">
        <svg width="13" height="10" viewBox="0 0 16 12" fill="var(--blue)"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
        디스코드 참가
      </button>
    </div>
    <div class="stats-bar">
      <div class="s-item"><div class="s-n" id="cnt">0</div><div class="s-l">거래 완료</div></div>
      <div class="s-item"><div class="s-n">98.7%</div><div class="s-l">고객 만족도</div></div>
      <div class="s-item"><div class="s-n">5분</div><div class="s-l">평균 배송</div></div>
      <div class="s-item"><div class="s-n">24/7</div><div class="s-l">자동 처리</div></div>
    </div>
  </section>

  <div class="divider"></div>

  <div id="shop-sec" class="shop">
    <div class="shop-head">
      <div class="shop-title" id="shop-ttl">전체 아이템 (12)</div>
      <select class="sort-sel" onchange="sortItems(this.value)">
        <option value="">기본 정렬</option>
        <option value="asc">낮은 가격순</option>
        <option value="desc">높은 가격순</option>
      </select>
    </div>
    <div class="grid" id="grid"></div>
  </div>

  <div class="bot">
    <h2>디스코드 봇 자동화</h2>
    <p>주문부터 배송까지 모두 자동 처리됩니다. 빠르고 신뢰할 수 있는 거래를 경험하세요.</p>
    <div class="cmd-list">
      <div class="cmd"><span class="cmd-k">/buy [아이템명]</span><span class="cmd-v">즉시 구매</span></div>
      <div class="cmd"><span class="cmd-k">/order [번호]</span><span class="cmd-v">주문 확인</span></div>
      <div class="cmd"><span class="cmd-k">/list</span><span class="cmd-v">전체 목록 보기</span></div>
      <div class="cmd"><span class="cmd-k">/balance</span><span class="cmd-v">잔액 확인</span></div>
    </div>
  </div>

  <footer>
    <p>© 2025 SailorPiece. All rights reserved.</p>
    <div class="foot-links">
      <span onclick="toast('이용약관')">이용약관</span>
      <span onclick="toast('개인정보처리방침')">개인정보처리방침</span>
    </div>
  </footer>
</div>

<!-- 주문 조회 -->
<div id="pg-orders" class="page">
  <div class="inner">
    <div class="pg-title">주문 조회</div>
    <div class="pg-sub">디스코드 ID로 주문 내역을 확인하세요.</div>
    <div class="row">
      <input class="inp" type="text" placeholder="디스코드 ID" id="dc-id">
      <button class="btn-fill" style="height:38px;padding:0 18px;font-size:12px" onclick="loadOrders()">조회</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>주문번호</th><th>아이템</th><th>금액</th><th>상태</th><th>날짜</th></tr></thead>
        <tbody id="order-rows"><tr><td colspan="5" style="text-align:center;padding:28px;color:var(--text3)">디스코드 ID를 입력하세요</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<!-- 관리자 -->
<div id="pg-admin" class="page">
  <div class="inner">
    <div class="pg-title">관리자 대시보드</div>
    <div class="pg-sub">판매 현황 및 주문 관리</div>
    <div class="a-grid">
      <div class="a-card"><div class="a-lbl">오늘 매출</div><div class="a-val">₩284,700</div></div>
      <div class="a-card"><div class="a-lbl">미처리 주문</div><div class="a-val">12</div></div>
      <div class="a-card"><div class="a-lbl">총 주문</div><div class="a-val">2,847</div></div>
      <div class="a-card"><div class="a-lbl">등록 아이템</div><div class="a-val">12</div></div>
    </div>
    <div class="sec-t">최근 주문</div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>번호</th><th>디스코드 ID</th><th>아이템</th><th>금액</th><th>상태</th><th></th></tr></thead>
        <tbody id="admin-rows"></tbody>
      </table>
    </div>
    <div class="sec-t">봇 설정</div>
    <div class="a-card" style="display:flex;gap:8px;align-items:center">
      <input class="inp" style="max-width:none;flex:1" type="text" placeholder="Discord Webhook URL">
      <button class="btn-fill" style="height:38px;padding:0 16px;font-size:12px;white-space:nowrap" onclick="toast('웹훅이 저장되었습니다.')">저장</button>
    </div>
  </div>
</div>

<!-- 장바구니 -->
<div class="cart-ov" id="cart-ov" onclick="if(event.target===this)closeCart()">
  <div class="drawer">
    <div class="d-head">
      <h2>장바구니</h2>
      <button class="cls" onclick="closeCart()">✕</button>
    </div>
    <div class="d-body" id="cart-body"></div>
    <div class="d-foot">
      <div class="d-tot"><span>합계</span><span id="cart-total">₩ 0</span></div>
      <button class="ord-btn" onclick="placeOrder()">
        <svg width="13" height="10" viewBox="0 0 16 12" fill="white"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
        디스코드로 주문하기
      </button>
      <div class="d-note">주문 후 디스코드에서 자동 처리됩니다.</div>
    </div>
  </div>
</div>

<!-- 관리자 모달 -->
<div class="m-ov" id="m-ov">
  <div class="modal">
    <h2>관리자 로그인</h2>
    <p>비밀번호를 입력하세요.</p>
    <input class="pw-inp" type="password" id="admin-pw" placeholder="비밀번호" onkeydown="if(event.key==='Enter')chkAdmin()">
    <div class="m-btns">
      <button class="m-no" onclick="closeAdmin()">취소</button>
      <button class="m-ok" onclick="chkAdmin()">로그인</button>
    </div>
  </div>
</div>

<div class="toast" id="toast-el"></div>

<script>
const ITEMS = [
  {id:1,  name:"세일러 소드",     desc:"높은 공격력의 상징적인 검",   price:15000, cat:"weapon",    stock:5,  tag:"hot",    tl:"인기"},
  {id:2,  name:"해왕의 창",       desc:"바다의 힘을 담은 강력한 창",  price:28000, cat:"weapon",    stock:2,  tag:"rare",   tl:"희귀"},
  {id:3,  name:"번개 활",         desc:"번개를 쏘는 원거리 무기",     price:35000, cat:"weapon",    stock:3,  tag:"rare",   tl:"희귀"},
  {id:4,  name:"별빛 단검",       desc:"빠른 공격 속도의 단검",       price:9500,  cat:"weapon",    stock:8,  tag:null,     tl:null},
  {id:5,  name:"세일러 방패",     desc:"바다의 기운으로 만든 방어구", price:12000, cat:"armor",     stock:10, tag:null,     tl:null},
  {id:6,  name:"산호 갑옷",       desc:"산호로 만든 가벼운 갑옷",    price:18000, cat:"armor",     stock:4,  tag:null,     tl:null},
  {id:7,  name:"용사 투구",       desc:"높은 방어력의 용사 투구",     price:16000, cat:"armor",     stock:6,  tag:"new",    tl:"신규"},
  {id:8,  name:"크리스탈 목걸이", desc:"마나 회복 악세서리",          price:8000,  cat:"accessory", stock:20, tag:"new",    tl:"신규"},
  {id:9,  name:"황금 반지",       desc:"행운을 가져다주는 반지",      price:6000,  cat:"accessory", stock:15, tag:null,     tl:null},
  {id:10, name:"마법 팔찌",       desc:"속도를 증가시키는 팔찌",      price:7500,  cat:"accessory", stock:12, tag:null,     tl:null},
  {id:11, name:"해적왕 스킨",     desc:"전설 등급 한정 스킨",         price:45000, cat:"skin",      stock:1,  tag:"legend", tl:"전설"},
  {id:12, name:"파도 스킨",       desc:"특수 파도 모션 스킨",         price:22000, cat:"skin",      stock:3,  tag:"new",    tl:"신규"},
];

const AD = [
  {id:"#2847",user:"SailorKing#1234", item:"해왕의 창",   price:"₩28,000",st:"p"},
  {id:"#2846",user:"OceanRider#5678", item:"해적왕 스킨", price:"₩45,000",st:"ok"},
  {id:"#2845",user:"WaveRunner#9012", item:"번개 활",     price:"₩35,000",st:"ok"},
  {id:"#2844",user:"SeaBoss#3456",    item:"파도 스킨",   price:"₩22,000",st:"no"},
  {id:"#2843",user:"BluePirate#7890", item:"세일러 소드", price:"₩15,000",st:"ok"},
];

const SL={p:"처리중",ok:"완료",no:"취소"}, SC={p:"st-p",ok:"st-ok",no:"st-no"};

const SVG={
  weapon:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m14.5 17.5-10 5 5-10 10-5-5 10zM12 12 7 7"/></svg>`,
  armor:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  accessory:`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>`,
  skin:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="12" cy="10" r="3"/></svg>`,
};

let cart=[], cur=[...ITEMS];

function renderGrid(list){
  const g=document.getElementById('grid');
  if(!list.length){g.innerHTML=`<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text3);font-size:13px">검색 결과가 없습니다.</div>`;return;}
  g.innerHTML=list.map(it=>`
    <div class="card">
      <div class="card-img">
        ${it.tag?`<div class="card-tag ${it.tag}">${it.tl}</div>`:''}
        <div class="card-icon">${SVG[it.cat]}</div>
      </div>
      <div class="card-body">
        <div class="card-name">${it.name}</div>
        <div class="card-desc">${it.desc}</div>
        <div class="card-foot">
          <div class="card-price">₩${it.price.toLocaleString()}<small> 원</small></div>
          <button class="add-btn" onclick="addCart(${it.id})">담기</button>
        </div>
        ${it.stock<=3?`<div class="card-stock">재고 ${it.stock}개</div>`:''}
      </div>
    </div>`).join('');
}

function sortItems(v){let s=[...cur];if(v==='asc')s.sort((a,b)=>a.price-b.price);if(v==='desc')s.sort((a,b)=>b.price-a.price);renderGrid(s);}

function addCart(id){
  const it=ITEMS.find(i=>i.id===id),ex=cart.find(c=>c.id===id);
  ex?ex.qty++:cart.push({...it,qty:1});
  updateCart();toast(`${it.name}이(가) 추가되었습니다.`);
}
function rmCart(id){cart=cart.filter(c=>c.id!==id);updateCart();}
function updateCart(){
  const total=cart.reduce((s,c)=>s+c.price*c.qty,0),qty=cart.reduce((s,c)=>s+c.qty,0);
  document.getElementById('cart-count').textContent=qty;
  document.getElementById('cart-total').textContent=`₩ ${total.toLocaleString()}`;
  const el=document.getElementById('cart-body');
  if(!cart.length){el.innerHTML=`<div class="empty"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text3)" stroke-width="1.5"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg><p>장바구니가 비어있습니다.</p></div>`;return;}
  el.innerHTML=cart.map(c=>`<div class="ci"><div class="ci-ic">${SVG[c.cat]}</div><div style="flex:1"><div class="ci-nm">${c.name} × ${c.qty}</div><div class="ci-pr">₩${(c.price*c.qty).toLocaleString()}</div></div><button class="ci-rm" onclick="rmCart(${c.id})">✕</button></div>`).join('');
}
function openCart(){document.getElementById('cart-ov').classList.add('on');}
function closeCart(){document.getElementById('cart-ov').classList.remove('on');}
function placeOrder(){
  if(!cart.length){toast('장바구니가 비어있습니다.');return;}
  const total=cart.reduce((s,c)=>s+c.price*c.qty,0);
  toast(`디스코드로 주문 전송! (₩${total.toLocaleString()})`);
  cart=[];updateCart();closeCart();
}

function goTab(tab,el){
  if(el){document.querySelectorAll('.ntab').forEach(t=>t.classList.remove('on'));el.classList.add('on');}
  ['shop','orders','admin'].forEach(t=>document.getElementById('pg-'+t).className=t===tab?'page on':'page');
}

function loadOrders(){
  const id=document.getElementById('dc-id').value.trim();
  if(!id){toast('디스코드 ID를 입력하세요.');return;}
  document.getElementById('order-rows').innerHTML=[
    {id:'#2840',item:'세일러 소드',    price:'₩15,000',st:'ok',date:'2025.04.10'},
    {id:'#2831',item:'크리스탈 목걸이',price:'₩8,000', st:'p', date:'2025.04.09'},
  ].map(r=>`<tr><td style="font-family:monospace;font-weight:600;font-size:11px">${r.id}</td><td>${r.item}</td><td style="font-weight:700;color:var(--blue)">${r.price}</td><td><span class="st ${SC[r.st]}">${SL[r.st]}</span></td><td>${r.date}</td></tr>`).join('');
  toast(`${id} 주문 내역 조회 완료!`);
}

function renderAdmin(){
  document.getElementById('admin-rows').innerHTML=AD.map(o=>`
    <tr>
      <td style="font-family:monospace;font-size:11px;font-weight:600">${o.id}</td>
      <td style="font-size:11px">${o.user}</td><td>${o.item}</td>
      <td style="font-weight:700;color:var(--blue)">${o.price}</td>
      <td><span class="st ${SC[o.st]}">${SL[o.st]}</span></td>
      <td>${o.st==='p'?`<button class="add-btn" onclick="toast('${o.id} 완료 처리!')">완료</button>`:'—'}</td>
    </tr>`).join('');
}

function openAdmin(){document.getElementById('m-ov').classList.add('on');setTimeout(()=>document.getElementById('admin-pw').focus(),80);}
function closeAdmin(){document.getElementById('m-ov').classList.remove('on');document.getElementById('admin-pw').value='';}
function chkAdmin(){
  if(document.getElementById('admin-pw').value==='admin1234'){closeAdmin();goTab('admin');renderAdmin();toast('관리자 패널 접속!');}
  else{toast('비밀번호가 올바르지 않습니다.');document.getElementById('admin-pw').value='';document.getElementById('admin-pw').focus();}
}

let tTimer;
function toast(msg){const el=document.getElementById('toast-el');el.textContent=msg;el.classList.add('on');clearTimeout(tTimer);tTimer=setTimeout(()=>el.classList.remove('on'),2500);}

renderGrid(ITEMS);updateCart();
(function(){const el=document.getElementById('cnt');let n=0;const id=setInterval(()=>{n=Math.min(n+55,2847);el.textContent=n.toLocaleString();if(n>=2847)clearInterval(id);},16);})();
</script>
</body>
</html>

여기서 이거 버튼 이상하게 뜨니까 고쳐주고 왼쪽 상단 세일러 피스 문구 없애서 공간 확보해
다른고는 절대 건들지마
