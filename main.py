<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SailorPiece - Premium Store</title>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* 전체 테마: 블랙 & 화이트 */
:root {
  --bg: #000000;
  --card-bg: #111111;
  --accent: #ffffff;
  --text-main: #ffffff;
  --text-sub: #a1a1a1;
  --border: rgba(255, 255, 255, 0.1);
}

* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'Pretendard', sans-serif;
  background: var(--bg);
  color: var(--text-main);
  -webkit-font-smoothing: antialiased;
  max-width: 1200px; /* PC 화면 최적화 */
  margin: 0 auto;
}

/* NAV - 로고 제거 및 PC 정렬 */
nav {
  position: fixed; top:0; left:50%; transform:translateX(-50%);
  width: 100%; max-width: 1200px;
  height: 64px; z-index: 100;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 30px;
}

.logo { display: none; } /* 요청사항: 로고 제거 */

.nav-tabs-pc {
  display: flex; gap: 8px;
}

.ntab {
  padding: 8px 18px; border-radius: 8px;
  font-size: 14px; font-weight: 600; color: var(--text-sub);
  cursor: pointer; border: none; background: transparent; transition: all .2s;
}
.ntab:hover { color: var(--accent); background: rgba(255,255,255,0.05); }
.ntab.on { background: var(--accent); color: #000; }

.nav-r { margin-left: auto; display: flex; gap: 12px; }

.nav-btn {
  height: 40px; padding: 0 16px;
  border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--border);
  background: transparent; color: var(--text-main);
  display: inline-flex; align-items: center; gap: 8px; transition: all .2s;
}
.nav-btn:hover { background: var(--accent); color: #000; }
.nav-btn.pri { background: var(--accent); color: #000; border: none; }

.cart-badge {
  background: #ff3b30; color: #fff;
  border-radius: 4px; padding: 1px 5px;
  font-size: 10px; font-weight: 800; margin-left: 4px;
}

/* HERO */
.hero {
  padding: 140px 30px 60px;
  text-align: left;
  background: radial-gradient(circle at top right, #1a1a1a, #000);
}
.eyebrow { font-size: 12px; font-weight: 700; color: var(--text-sub); letter-spacing: 2px; margin-bottom: 12px; }
.hero h1 { font-size: 52px; font-weight: 800; line-height: 1.2; margin-bottom: 24px; }
.hero h1 em { font-style: normal; color: var(--text-sub); }

.stats-bar {
  display: flex; gap: 40px; margin-top: 40px;
  padding: 24px 0; border-top: 1px solid var(--border);
}
.s-n { font-size: 24px; font-weight: 700; color: var(--accent); }
.s-l { font-size: 12px; color: var(--text-sub); margin-top: 4px; }

/* GRID & CARDS */
.shop { padding: 60px 30px; }
.shop-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; } /* PC 4열 배치 */

.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden; transition: all .3s;
}
.card:hover { transform: translateY(-8px); border-color: var(--accent); }
.card-img { width: 100%; aspect-ratio: 1; background: #0a0a0a; display: flex; align-items: center; justify-content: center; position: relative; }
.card-icon { width: 60px; height: 60px; color: var(--accent); opacity: 0.8; }
.card-tag { position: absolute; top: 12px; left: 12px; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 4px; background: var(--accent); color: #000; }

.card-body { padding: 20px; }
.card-name { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
.card-desc { font-size: 13px; color: var(--text-sub); margin-bottom: 20px; height: 36px; overflow: hidden; }
.card-foot { display: flex; align-items: center; justify-content: space-between; }
.card-price { font-size: 18px; font-weight: 700; }
.add-btn {
  padding: 8px 16px; background: transparent; border: 1px solid var(--accent);
  color: var(--accent); border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; transition: 0.2s;
}
.add-btn:hover { background: var(--accent); color: #000; }

/* TABLE 스타일 */
.inner { padding: 120px 30px; }
.tbl-wrap { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #1a1a1a; padding: 15px; text-align: left; font-size: 12px; color: var(--text-sub); }
td { padding: 15px; border-bottom: 1px solid var(--border); font-size: 14px; }

/* 기타 */
.inp { background: #1a1a1a; border: 1px solid var(--border); color: #fff; padding: 10px 15px; border-radius: 8px; outline: none; }
.toast { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: var(--accent); color: #000; padding: 12px 24px; border-radius: 8px; font-weight: 700; display: none; z-index: 1000; }

@media (max-width: 1024px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>

<nav>
  <div class="nav-tabs-pc">
    <button class="ntab on" onclick="goTab('shop',this)">쇼핑몰</button>
    <button class="ntab" onclick="goTab('orders',this)">주문 조회</button>
    <button class="ntab" onclick="openAdmin()">관리자</button>
  </div>
  <div class="nav-r">
    <button class="nav-btn" onclick="toast('디스코드 서버로 이동합니다.')">디스코드</button>
    <button class="nav-btn pri" onclick="openCart()">장바구니 <span class="cart-badge" id="cart-count">0</span></button>
  </div>
</nav>

<div id="pg-shop" class="page on">
  <section class="hero">
    <div class="eyebrow">PREMIUM ITEM STORE</div>
    <h1>세일러 피스<br><em>아이템 스토어</em></h1>
    <div class="stats-bar">
      <div class="s-item"><div class="s-n">2,847+</div><div class="s-l">누적 거래</div></div>
      <div class="s-item"><div class="s-n">99.9%</div><div class="s-l">만족도</div></div>
      <div class="s-item"><div class="s-n">24/7</div><div class="s-l">자동 배송</div></div>
    </div>
  </section>

  <div class="shop">
    <div class="shop-head">
      <h2 style="font-size:24px;">Items</h2>
    </div>
    <div class="grid" id="grid"></div>
  </div>
</div>

<div id="pg-orders" class="page" style="display:none; padding-top:100px;">
  <div class="inner">
    <h1>주문 조회</h1>
    <div style="margin: 20px 0; display:flex; gap:10px;">
      <input class="inp" type="text" placeholder="디스코드 ID 입력" id="dc-id">
      <button class="add-btn" onclick="loadOrders()">조회하기</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>주문번호</th><th>아이템</th><th>금액</th><th>상태</th></tr></thead>
        <tbody id="order-rows"><tr><td colspan="4" style="text-align:center; color:gray;">조회 결과가 없습니다.</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<div class="toast" id="toast-el"></div>

<script>
const ITEMS = [
  {id:1, name:"세일러 소드", desc:"전설적인 공격력을 가진 명검", price:15000, cat:"weapon", tag:"HOT"},
  {id:2, name:"해왕의 창", desc:"심해의 힘을 끌어쓰는 창", price:28000, cat:"weapon", tag:"RARE"},
  {id:3, name:"해적왕 스킨", desc:"최상위 랭커를 위한 한정판", price:45000, cat:"skin", tag:"LEGEND"},
  {id:4, name:"산호 갑옷", desc:"가볍고 견고한 고성능 갑옷", price:18000, cat:"armor", tag:null}
];

function renderGrid() {
  const g = document.getElementById('grid');
  g.innerHTML = ITEMS.map(it => `
    <div class="card">
      <div class="card-img">
        ${it.tag ? `<div class="card-tag">${it.tag}</div>` : ''}
        <div class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg></div>
      </div>
      <div class="card-body">
        <div class="card-name">${it.name}</div>
        <div class="card-desc">${it.desc}</div>
        <div class="card-foot">
          <div class="card-price">₩${it.price.toLocaleString()}</div>
          <button class="add-btn" onclick="toast('${it.name} 추가됨')">담기</button>
        </div>
      </div>
    </div>`).join('');
}

function goTab(tab, el) {
  document.querySelectorAll('.ntab').forEach(b => b.classList.remove('on'));
  el.classList.add('on');
  document.getElementById('pg-shop').style.display = tab === 'shop' ? 'block' : 'none';
  document.getElementById('pg-orders').style.display = tab === 'orders' ? 'block' : 'none';
}

function toast(m) {
  const t = document.getElementById('toast-el');
  t.textContent = m; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2000);
}

renderGrid();
</script>
</body>
</html>
