<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SailorPiece - Multi Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* 테마 설정: 블랙 & 화이트 */
:root {
  --bg: #000000;
  --card-bg: #111111;
  --accent: #ffffff;
  --text-main: #ffffff;
  --text-sub: #a1a1a1;
  --border: rgba(255, 255, 255, 0.15);
}

* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'Pretendard', sans-serif;
  background: var(--bg);
  color: var(--text-main);
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
}

/* 네비게이션: PC/모바일 호환 */
nav {
  position: fixed; top:0; left:0; right:0;
  height: 60px; z-index: 1000;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(15px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 5%; /* 화면 크기에 따른 가변 패딩 */
}

/* 로고 제거 후 공간 확보 */
.logo { display: none; }

.nav-tabs {
  display: flex; gap: 5px;
}

.ntab {
  padding: 8px 16px; 
  border-radius: 999px; /* 버튼 둥글게 */
  font-size: 14px; font-weight: 600; color: var(--text-sub);
  cursor: pointer; border: none; background: transparent; transition: 0.2s;
}
.ntab.on { background: var(--accent); color: #000; }
.ntab:hover:not(.on) { color: var(--accent); background: rgba(255,255,255,0.1); }

.nav-r { margin-left: auto; display: flex; gap: 8px; }

.nav-btn {
  height: 36px; padding: 0 14px;
  border-radius: 999px; /* 버튼 둥글게 */
  font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--border);
  background: transparent; color: var(--text-main);
  display: inline-flex; align-items: center; gap: 6px; transition: 0.2s;
}
.nav-btn:hover { background: var(--accent); color: #000; }

.cart-badge {
  background: #ffffff; color: #000;
  border-radius: 999px; min-width: 18px; padding: 0 5px;
  font-size: 10px; font-weight: 800; margin-left: 4px;
}

/* 레이아웃 컨테이너 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* HERO 섹션 */
.hero {
  padding: 120px 0 60px;
  text-align: center;
}
.hero h1 { font-size: clamp(32px, 5vw, 52px); font-weight: 800; margin-bottom: 15px; }
.hero p { color: var(--text-sub); font-size: 16px; }

/* 아이템 그리드: 모바일 2열, PC 4열 */
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* 모바일 기본 2열 */
  gap: 15px;
  padding-bottom: 50px;
}

@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(4, 1fr); } /* PC 4열 */
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 20px; /* 카드도 둥글게 */
  overflow: hidden; transition: 0.3s;
}
.card:hover { border-color: var(--accent); transform: translateY(-5px); }

.card-img {
  width: 100%; aspect-ratio: 1;
  background: #0a0a0a; display: flex; align-items: center; justify-content: center;
  position: relative; border-bottom: 1px solid var(--border);
}
.card-icon { width: 50px; height: 50px; color: var(--accent); }

.card-tag {
  position: absolute; top: 12px; left: 12px;
  font-size: 10px; font-weight: 700; padding: 4px 10px;
  border-radius: 999px; background: var(--accent); color: #000;
}

.card-body { padding: 15px; }
.card-name { font-size: 15px; font-weight: 700; margin-bottom: 5px; }
.card-price { font-size: 17px; font-weight: 700; color: var(--accent); margin-bottom: 12px; }

.add-btn {
  width: 100%; height: 36px;
  background: transparent; border: 1px solid var(--accent);
  color: var(--accent); border-radius: 999px; /* 버튼 둥글게 */
  font-size: 12px; font-weight: 700; cursor: pointer; transition: 0.2s;
}
.add-btn:hover { background: var(--accent); color: #000; }

/* 주문 조회 페이지 */
.page { display: none; padding-top: 100px; }
.page.active { display: block; }

.inp {
  width: 100%; max-width: 300px; height: 40px;
  background: #1a1a1a; border: 1px solid var(--border);
  color: #fff; padding: 0 15px; border-radius: 999px; outline: none;
}

/* 토스트 알림 */
.toast {
  position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
  background: var(--accent); color: #000;
  padding: 10px 20px; border-radius: 999px;
  font-size: 13px; font-weight: 700;
  display: none; z-index: 2000; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
</style>
</head>
<body>

<nav>
  <div class="nav-tabs">
    <button class="ntab on" onclick="showPage('shop', this)">쇼핑몰</button>
    <button class="ntab" onclick="showPage('orders', this)">주문조회</button>
  </div>
  <div class="nav-r">
    <button class="nav-btn" onclick="toast('디스코드로 이동')">디스코드</button>
    <button class="nav-btn" style="background:white; color:black; border:none;">
      장바구니 <span class="cart-badge">0</span>
    </button>
  </div>
</nav>

<div id="shop" class="page active">
  <div class="container">
    <section class="hero">
      <div style="font-size:11px; font-weight:700; letter-spacing:2px; color:gray; margin-bottom:10px;">SAILOR PIECE STORE</div>
      <h1>아이템 스토어</h1>
      <p>모든 거래는 자동으로 즉시 처리됩니다.</p>
    </section>
    
    <div class="grid" id="item-grid"></div>
  </div>
</div>

<div id="orders" class="page">
  <div class="container">
    <h1 style="margin-bottom:20px;">주문 조회</h1>
    <div style="display:flex; gap:10px; margin-bottom:30px;">
      <input type="text" class="inp" placeholder="디스코드 ID 입력">
      <button class="nav-btn" style="background:white; color:black;" onclick="toast('조회 중...')">조회</button>
    </div>
    <div style="color:gray; text-align:center; padding:50px; border:1px dashed var(--border); border-radius:20px;">
      조회된 주문 내역이 없습니다.
    </div>
  </div>
</div>

<div class="toast" id="toast-el"></div>

<script>
const ITEMS = [
  {id:1, name:"세일러 소드", price:15000, tag:"HOT"},
  {id:2, name:"해왕의 창", price:28000, tag:"RARE"},
  {id:3, name:"해적왕 스킨", price:45000, tag:"LEGEND"},
  {id:4, name:"산호 갑옷", price:18000, tag:null},
  {id:5, name:"별빛 단검", price:9500, tag:null},
  {id:6, name:"마법 반지", price:12000, tag:"NEW"}
];

function renderItems() {
  const grid = document.getElementById('item-grid');
  grid.innerHTML = ITEMS.map(it => `
    <div class="card">
      <div class="card-img">
        ${it.tag ? `<div class="card-tag">${it.tag}</div>` : ''}
        <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
      </div>
      <div class="card-body">
        <div class="card-name">${it.name}</div>
        <div class="card-price">₩${it.price.toLocaleString()}</div>
        <button class="add-btn" onclick="toast('${it.name} 장바구니 담기')">담기</button>
      </div>
    </div>`).join('');
}

function showPage(pageId, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.ntab').forEach(b => b.classList.remove('on'));
  document.getElementById(pageId).classList.add('active');
  btn.classList.add('on');
}

function toast(msg) {
  const el = document.getElementById('toast-el');
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 2000);
}

renderItems();
</script>
</body>
</html>
