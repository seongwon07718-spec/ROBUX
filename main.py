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
* { margin: 0; padding: 0; box-sizing: border-box; }

html { background: #ffffff !important; color-scheme: light; }

:root {
  --blue: #0ea5e9;
  --blue-dark: #0284c7;
  --sky: #f0f9ff;
  --sky2: #e0f2fe;
  --sky3: #bae6fd;
  --text: #0f172a;
  --text2: #475569;
  --text3: #94a3b8;
  --border: rgba(14, 165, 233, 0.12);
  --glass: rgba(255, 255, 255, 0.6);
}

body {
  font-family: 'Pretendard', -apple-system, sans-serif;
  background: #ffffff !important;
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* ── NAV ── */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  height: 56px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
}

.logo {
  font-size: 16px; font-weight: 700;
  color: var(--blue); letter-spacing: -0.3px;
}

.nav-center {
  display: flex; gap: 4px;
  background: rgba(14, 165, 233, 0.07);
  border: 1px solid var(--border);
  border-radius: 999px; padding: 4px;
}

.ntab {
  padding: 6px 18px; border-radius: 999px;
  font-size: 13px; font-weight: 500;
  color: var(--text2); cursor: pointer;
  border: none; background: transparent;
  transition: all 0.15s;
}
.ntab:hover { color: var(--blue); }
.ntab.on {
  background: white;
  color: var(--blue); font-weight: 600;
  box-shadow: 0 1px 8px rgba(14,165,233,0.15);
}

.nav-right { display: flex; gap: 8px; align-items: center; }

.nav-btn {
  height: 34px; padding: 0 14px;
  border-radius: 999px; font-size: 13px; font-weight: 500;
  cursor: pointer; border: 1px solid var(--border);
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(10px);
  color: var(--text2); transition: all 0.15s;
  display: inline-flex; align-items: center; gap: 6px;
  white-space: nowrap;
}
.nav-btn:hover { background: white; color: var(--blue); }
.nav-btn.primary {
  background: rgba(14,165,233,0.1);
  color: var(--blue); font-weight: 600;
  border-color: rgba(14,165,233,0.2);
}
.nav-btn.primary:hover { background: rgba(14,165,233,0.18); }

.badge {
  background: var(--blue); color: white;
  border-radius: 999px; width: 16px; height: 16px;
  font-size: 9px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}

/* ── PAGE ── */
.page { display: none; }
.page.on { display: block; }

/* ── HERO ── */
.hero {
  min-height: auto;
  padding: 96px 24px 28px;
  background: linear-gradient(170deg, #f0f9ff 0%, #ffffff 60%);
  text-align: center;
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.hero::before {
  content: ''; position: absolute;
  top: -80px; left: 50%; transform: translateX(-50%);
  width: 600px; height: 500px;
  background: radial-gradient(ellipse, rgba(56,189,248,0.12) 0%, transparent 70%);
  pointer-events: none;
}

.hero-eyebrow {
  font-size: 11px; font-weight: 600;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--blue); margin-bottom: 8px;
  opacity: 0; animation: up .5s .05s forwards;
}

.hero h1 {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 700; letter-spacing: -1.5px; line-height: 1.1;
  color: var(--text); margin-bottom: 0;
  opacity: 0; animation: up .5s .13s forwards;
}
.hero h1 em { font-style: normal; color: var(--blue); }

.hero-btns {
  display: flex; gap: 10px; justify-content: center;
  opacity: 0; animation: up .5s .29s forwards;
  margin-top: 12px; margin-bottom: 10px;
}

.stats-wrap { padding: 0; margin: 0; }

.hero-desc { display: none; }

.btn-fill {
  height: 38px; padding: 0 22px;
  border-radius: 999px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: none;
  background: var(--blue); color: white;
  box-shadow: 0 4px 16px rgba(14,165,233,0.3);
  transition: all .15s;
  display: inline-flex; align-items: center; gap: 8px;
}
.btn-fill:hover { background: var(--blue-dark); transform: translateY(-1px); }

.btn-glass {
  height: 38px; padding: 0 22px;
  border-radius: 999px; font-size: 13px; font-weight: 500;
  cursor: pointer;
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  color: var(--blue); transition: all .15s;
  display: inline-flex; align-items: center; gap: 8px;
}
.btn-glass:hover { background: rgba(255,255,255,0.95); }

/* ── STATS BAR ── */
.stats-bar {
  display: inline-flex; align-items: center;
  margin-top: 14px;
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(14,165,233,0.09),
              inset 0 1px 0 rgba(255,255,255,0.9);
  padding: 0 4px;
}

.stats-wrap { padding: 0; margin: 0; }
.stats-item {
  padding: 10px 18px;
  text-align: center;
}
.stats-n {
  font-size: 15px; font-weight: 700;
  color: var(--blue); letter-spacing: -0.5px;
}
.stats-l {
  font-size: 10px; color: var(--text3);
  margin-top: 1px; font-weight: 500;
}
.stats-div {
  width: 1px; height: 24px;
  background: rgba(14,165,233,0.15);
  flex-shrink: 0;
}

/* ── STATS (old, hidden) ── */
.stats { display: none; }

/* ── SHOP ── */
.shop-layout {
  max-width: 1200px; margin: 0 auto;
  padding: 16px 20px;
  display: flex; gap: 24px;
}

/* ── SIDEBAR ── */
.sidebar { width: 190px; flex-shrink: 0; }

.glass-card {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 16px;
  box-shadow: 0 2px 20px rgba(14,165,233,0.06),
              inset 0 1px 0 rgba(255,255,255,0.9);
  padding: 16px;
  margin-bottom: 12px;
}

.sb-label {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--text3); margin-bottom: 10px;
}

.cat-item {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; border: none; background: transparent;
  border-radius: 10px; padding: 8px 10px;
  font-size: 13px; font-weight: 500; color: var(--text2);
  cursor: pointer; transition: all .14s; margin-bottom: 2px;
  text-align: left;
}
.cat-item:hover { background: rgba(14,165,233,0.08); color: var(--blue); }
.cat-item.on { background: rgba(14,165,233,0.1); color: var(--blue); font-weight: 600; }
.cat-cnt {
  font-size: 10px; color: var(--blue);
  background: rgba(14,165,233,0.1);
  border-radius: 999px; padding: 1px 7px;
}

.pf-row { display: flex; gap: 6px; margin-bottom: 8px; }
.pf-inp {
  flex: 1; border: 1px solid var(--border); border-radius: 9px;
  padding: 7px 9px; font-size: 12px; color: var(--text);
  background: rgba(255,255,255,0.8); outline: none;
}
.pf-inp:focus { border-color: var(--blue); }
.pf-inp::placeholder { color: var(--text3); }

.pf-btn {
  width: 100%; padding: 8px; border-radius: 999px;
  background: rgba(14,165,233,0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(14,165,233,0.18);
  color: var(--blue); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .14s;
}
.pf-btn:hover { background: rgba(14,165,233,0.2); }

/* ── ITEMS AREA ── */
.items-area { flex: 1; min-width: 0; }

.items-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.items-title { font-size: 15px; font-weight: 700; letter-spacing: -0.3px; }

.sort-sel {
  height: 32px; padding: 0 12px;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border); border-radius: 999px;
  font-size: 12px; color: var(--text2); outline: none; cursor: pointer;
}

/* ── GRID ── */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 12px;
}

.item-card {
  background: #ffffff;
  border: 1px solid rgba(14,165,233,0.1);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 2px 14px rgba(14,165,233,0.06);
  transition: transform .2s, box-shadow .2s;
}
.item-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(14,165,233,0.13);
}

.item-img {
  width: 100%; aspect-ratio: 1;
  background: #f8fbff;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  border-bottom: 1px solid rgba(14,165,233,0.07);
}

.item-icon {
  width: 48px; height: 48px;
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(8px);
  border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(14,165,233,0.12);
}
.item-icon svg { width: 24px; height: 24px; color: var(--blue); stroke-width: 1.7; }

.item-tag {
  position: absolute; top: 8px; left: 8px;
  font-size: 9px; font-weight: 700;
  padding: 3px 8px; border-radius: 999px;
  backdrop-filter: blur(6px);
}
.tag-hot    { background: rgba(254,243,199,0.9); color: #d97706; }
.tag-rare   { background: rgba(237,233,254,0.9); color: #7c3aed; }
.tag-new    { background: rgba(209,250,229,0.9); color: #059669; }
.tag-legend { background: rgba(254,226,226,0.9); color: #dc2626; }

.item-body { padding: 11px 12px; background: #ffffff; }
.item-name { font-size: 13px; font-weight: 700; margin-bottom: 3px; letter-spacing: -0.2px; }
.item-desc { font-size: 11px; color: var(--text3); margin-bottom: 10px; line-height: 1.4; }

.item-foot {
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
}
.item-price { font-size: 14px; font-weight: 700; color: var(--blue); }
.item-price span { font-size: 9px; color: var(--text3); font-weight: 400; }

.add-btn {
  height: 28px; padding: 0 12px;
  background: rgba(14,165,233,0.1);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(14,165,233,0.2);
  border-radius: 999px; font-size: 11px; font-weight: 700;
  color: var(--blue); cursor: pointer; transition: all .13s;
  white-space: nowrap;
}
.add-btn:hover { background: rgba(14,165,233,0.2); }
.add-btn:active { transform: scale(0.95); }

.item-stock { font-size: 10px; color: #f87171; font-weight: 600; margin-top: 6px; }

/* ── BOT ── */
.bot-section {
  background: linear-gradient(150deg, #f0f9ff 0%, #fff 55%);
  border-top: 1px solid var(--border);
  padding: 56px 48px;
  display: flex; gap: 64px;
  align-items: center; justify-content: center;
}

.bot-info h2 { font-size: 26px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 10px; }
.bot-info p { font-size: 14px; color: var(--text2); line-height: 1.7; margin-bottom: 20px; max-width: 400px; }

.cmd-list { display: flex; flex-direction: column; gap: 6px; }
.cmd {
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 11px; padding: 10px 14px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
}
.cmd-k { font-family: 'SF Mono', monospace; font-size: 12px; font-weight: 700; color: var(--blue); }
.cmd-v { font-size: 11px; color: var(--text3); }

.bot-vis { text-align: center; flex-shrink: 0; }
.bot-avatar {
  width: 84px; height: 84px;
  background: linear-gradient(135deg, var(--blue) 0%, #38bdf8 100%);
  border-radius: 22px;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
  box-shadow: 0 8px 28px rgba(14,165,233,0.3);
}
.bot-avatar svg { width: 42px; height: 42px; color: white; stroke-width: 1.6; }
.online-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 600; color: #10b981;
}
.online-tag::before {
  content: ''; width: 7px; height: 7px;
  background: #10b981; border-radius: 50%;
  animation: blink 2s ease infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.4} }
.bot-id { font-size: 11px; color: var(--text3); margin-top: 4px; }

/* ── FOOTER ── */
footer {
  border-top: 1px solid var(--border);
  padding: 18px 48px;
  display: flex; justify-content: space-between; align-items: center;
}
footer p { font-size: 11px; color: var(--text3); }
.foot-links { display: flex; gap: 16px; }
.foot-links span { font-size: 11px; color: var(--text3); cursor: pointer; }
.foot-links span:hover { color: var(--blue); }

/* ── INNER PAGES ── */
.inner { max-width: 900px; margin: 76px auto 0; padding: 40px 36px; }
.inner-lg { max-width: 1080px; }
.pg-title { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }
.pg-sub { font-size: 13px; color: var(--text2); margin-bottom: 24px; }

.search-row { display: flex; gap: 8px; margin-bottom: 22px; align-items: center; }
.search-inp {
  height: 38px; padding: 0 16px;
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border); border-radius: 999px;
  font-size: 13px; color: var(--text); outline: none; width: 220px;
}
.search-inp:focus { border-color: var(--blue); }
.search-inp::placeholder { color: var(--text3); }

/* ── TABLE ── */
.tbl-wrap {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 2px 16px rgba(14,165,233,0.06),
              inset 0 1px 0 rgba(255,255,255,0.9);
  margin-bottom: 28px;
}
table { width: 100%; border-collapse: collapse; }
th {
  background: rgba(224,242,254,0.5);
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .7px;
  color: var(--text3); padding: 11px 16px; text-align: left;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 12px 16px; font-size: 13px; color: var(--text2);
  border-bottom: 1px solid var(--border);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(14,165,233,0.02); }

.st {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 999px;
  font-size: 11px; font-weight: 600;
}
.st::before { content: ''; width: 5px; height: 5px; border-radius: 50%; }
.st-p  { background: #fef9c3; color: #a16207; } .st-p::before  { background: #eab308; }
.st-ok { background: #d1fae5; color: #065f46; } .st-ok::before { background: #10b981; }
.st-no { background: #fee2e2; color: #991b1b; } .st-no::before { background: #ef4444; }

/* ── ADMIN STATS ── */
.a-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
  gap: 12px; margin-bottom: 24px;
}
.a-card {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 14px; padding: 16px;
  box-shadow: 0 2px 12px rgba(14,165,233,0.05),
              inset 0 1px 0 rgba(255,255,255,0.9);
}
.a-label { font-size: 11px; color: var(--text3); font-weight: 500; margin-bottom: 6px; }
.a-val { font-size: 24px; font-weight: 700; color: var(--blue); letter-spacing: -0.6px; }

.sec-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; letter-spacing: -0.2px; }

/* ── CART ── */
.cart-ov {
  display: none; position: fixed; inset: 0;
  background: rgba(186,230,253,0.2);
  z-index: 200; justify-content: flex-end;
  backdrop-filter: blur(6px);
}
.cart-ov.on { display: flex; }

.cart-drawer {
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(28px) saturate(180%);
  border-left: 1px solid rgba(255,255,255,0.9);
  width: 330px; height: 100%; padding: 24px;
  display: flex; flex-direction: column;
  animation: slide .22s ease;
  box-shadow: -4px 0 28px rgba(14,165,233,0.08),
              inset 1px 0 0 rgba(255,255,255,0.6);
}
@keyframes slide { from{transform:translateX(100%)} to{transform:translateX(0)} }

.d-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.d-head h2 { font-size: 16px; font-weight: 700; }
.close-btn {
  width: 28px; height: 28px; border-radius: 50%;
  background: rgba(14,165,233,0.08);
  border: 1px solid rgba(14,165,233,0.14);
  color: var(--blue); font-size: 12px; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all .13s;
}
.close-btn:hover { background: rgba(14,165,233,0.17); }

.d-body { flex: 1; overflow-y: auto; }

.ci {
  display: flex; gap: 10px; padding: 11px 0;
  border-bottom: 1px solid var(--border); align-items: center;
}
.ci-icon {
  width: 38px; height: 38px; flex-shrink: 0;
  background: rgba(224,242,254,0.8);
  backdrop-filter: blur(6px);
  border-radius: 10px; border: 1px solid rgba(255,255,255,0.9);
  display: flex; align-items: center; justify-content: center;
}
.ci-icon svg { width: 18px; height: 18px; color: var(--blue); stroke-width: 1.7; }
.ci-name { font-size: 13px; font-weight: 600; }
.ci-price { font-size: 11px; color: var(--text3); margin-top: 1px; }
.ci-rm { background: none; border: none; color: var(--text3); cursor: pointer; font-size: 14px; transition: color .13s; margin-left: auto; }
.ci-rm:hover { color: #f87171; }

.d-foot { padding-top: 14px; border-top: 1px solid var(--border); margin-top: 10px; }
.d-total { display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; margin-bottom: 12px; }

.order-btn {
  width: 100%; height: 44px;
  background: #5865F2; color: white; border: none;
  border-radius: 999px; font-size: 13px; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 7px;
  box-shadow: 0 4px 16px rgba(88,101,242,0.28);
  transition: opacity .15s;
}
.order-btn:hover { opacity: .88; }

.d-note { text-align: center; font-size: 10px; color: var(--text3); margin-top: 8px; line-height: 1.5; }

.cart-empty { text-align: center; padding: 40px 0; }
.cart-empty p { font-size: 13px; color: var(--text3); margin-top: 10px; }

/* ── MODAL ── */
.modal-ov {
  display: none; position: fixed; inset: 0;
  background: rgba(186,230,253,0.2);
  z-index: 300; align-items: center; justify-content: center;
  backdrop-filter: blur(10px);
}
.modal-ov.on { display: flex; }
.modal {
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.95);
  border-radius: 20px; padding: 28px; width: 320px;
  box-shadow: 0 20px 50px rgba(14,165,233,0.1),
              inset 0 1px 0 rgba(255,255,255,0.9);
  animation: fadeup .2s ease;
}
.modal h2 { font-size: 17px; font-weight: 700; margin-bottom: 4px; }
.modal p { font-size: 12px; color: var(--text2); margin-bottom: 16px; }
.pw-inp {
  width: 100%; height: 40px; padding: 0 14px;
  border: 1px solid var(--border); border-radius: 10px;
  font-size: 14px; color: var(--text);
  background: rgba(255,255,255,0.8); outline: none; margin-bottom: 12px;
}
.pw-inp:focus { border-color: var(--blue); }
.modal-btns { display: flex; gap: 8px; }
.m-cancel {
  flex: 1; height: 38px; border-radius: 999px;
  background: rgba(14,165,233,0.07); border: 1px solid var(--border);
  font-size: 13px; font-weight: 600; color: var(--text2); cursor: pointer; transition: all .13s;
}
.m-cancel:hover { background: rgba(14,165,233,0.13); }
.m-ok {
  flex: 1; height: 38px; border-radius: 999px;
  background: var(--blue); border: none;
  font-size: 13px; font-weight: 600; color: white; cursor: pointer; transition: background .13s;
}
.m-ok:hover { background: var(--blue-dark); }

/* ── TOAST ── */
.toast {
  position: fixed; bottom: 24px; left: 50%;
  transform: translateX(-50%) translateY(50px);
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  color: var(--text); border-radius: 999px;
  padding: 10px 20px; font-size: 12px; font-weight: 500;
  z-index: 999; transition: transform .22s ease;
  box-shadow: 0 4px 20px rgba(14,165,233,0.1);
  white-space: nowrap;
}
.toast.on { transform: translateX(-50%) translateY(0); }

@keyframes up { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeup { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

@media (max-width: 768px) {
  nav { padding: 0 20px; }
  .nav-center { display: none; }
  .sidebar { display: none; }
  .shop-layout { padding: 20px; }
  .hero { padding: 90px 20px 48px; }
  .bot-section { flex-direction: column; padding: 40px 20px; }
  .bot-vis { display: none; }
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="logo">SailorPiece</div>
  <div class="nav-center">
    <button class="ntab on" onclick="goTab('shop',this)">쇼핑몰</button>
    <button class="ntab" onclick="goTab('orders',this)">주문 조회</button>
    <button class="ntab" onclick="openAdmin()">관리자</button>
  </div>
  <div class="nav-right">
    <button class="nav-btn" onclick="toast('디스코드 서버로 이동합니다.')">
      <svg width="14" height="11" viewBox="0 0 16 12" fill="var(--blue)"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
      디스코드
    </button>
    <button class="nav-btn primary" onclick="openCart()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" stroke-width="2.2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      장바구니 <div class="badge" id="cart-count">0</div>
    </button>
  </div>
</nav>

<!-- 쇼핑몰 페이지 -->
<div id="pg-shop" class="page on">

  <section class="hero">
    <div class="hero-eyebrow">Sailor Piece — Official Item Store</div>
    <h1>세일러 피스<br><em>아이템 스토어</em></h1>
    <div class="hero-btns">
    <div class="hero-btns">
      <button class="btn-fill" onclick="document.getElementById('shop-start').scrollIntoView({behavior:'smooth'})">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
        아이템 보기
      </button>
      <button class="btn-glass" onclick="toast('초대 링크가 복사되었습니다.')">
        <svg width="14" height="11" viewBox="0 0 16 12" fill="var(--blue)"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
        디스코드 참가
      </button>
    </div>
    </div>
    <div class="stats-wrap">
      <div class="stats-bar">
        <div class="stats-item"><div class="stats-n" id="cnt">0</div><div class="stats-l">거래 완료</div></div>
        <div class="stats-div"></div>
        <div class="stats-item"><div class="stats-n">98.7%</div><div class="stats-l">고객 만족도</div></div>
        <div class="stats-div"></div>
        <div class="stats-item"><div class="stats-n">5분</div><div class="stats-l">평균 배송</div></div>
        <div class="stats-div"></div>
        <div class="stats-item"><div class="stats-n">24/7</div><div class="stats-l">자동 처리</div></div>
      </div>
    </div>
  </section>

  <div style="height:1px;background:rgba(14,165,233,0.12);margin:0 24px;"></div>

  <div id="shop-start" class="shop-layout">

    <!-- 사이드바 -->
    <div class="sidebar">
      <div class="glass-card">
        <div class="sb-label">카테고리</div>
        <button class="cat-item on" onclick="filterCat('all',this)">전체 <span class="cat-cnt">12</span></button>
        <button class="cat-item" onclick="filterCat('weapon',this)">무기 <span class="cat-cnt">4</span></button>
        <button class="cat-item" onclick="filterCat('armor',this)">방어구 <span class="cat-cnt">3</span></button>
        <button class="cat-item" onclick="filterCat('accessory',this)">악세서리 <span class="cat-cnt">3</span></button>
        <button class="cat-item" onclick="filterCat('skin',this)">스킨 <span class="cat-cnt">2</span></button>
      </div>
      <div class="glass-card">
        <div class="sb-label">가격 필터</div>
        <div class="pf-row">
          <input class="pf-inp" type="number" placeholder="최소" id="pmin">
          <input class="pf-inp" type="number" placeholder="최대" id="pmax">
        </div>
        <button class="pf-btn" onclick="applyFilter()">적용</button>
      </div>
    </div>

    <!-- 아이템 영역 -->
    <div class="items-area">
      <div class="items-header">
        <div class="items-title" id="items-title">전체 아이템 (12)</div>
        <select class="sort-sel" onchange="sortItems(this.value)">
          <option value="">기본 정렬</option>
          <option value="asc">낮은 가격순</option>
          <option value="desc">높은 가격순</option>
        </select>
      </div>
      <div class="grid" id="grid"></div>
    </div>

  </div>

  <!-- 봇 섹션 -->
  <div class="bot-section">
    <div class="bot-info">
      <h2>디스코드 봇 자동화</h2>
      <p>주문부터 배송까지 모두 자동 처리됩니다. 빠르고 신뢰할 수 있는 거래를 경험하세요.</p>
      <div class="cmd-list">
        <div class="cmd"><span class="cmd-k">/buy [아이템명]</span><span class="cmd-v">즉시 구매</span></div>
        <div class="cmd"><span class="cmd-k">/order [번호]</span><span class="cmd-v">주문 확인</span></div>
        <div class="cmd"><span class="cmd-k">/list</span><span class="cmd-v">전체 목록 보기</span></div>
        <div class="cmd"><span class="cmd-k">/balance</span><span class="cmd-v">잔액 확인</span></div>
      </div>
    </div>
    <div class="bot-vis">
      <div class="bot-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/></svg>
      </div>
      <div class="online-tag">온라인</div>
      <div class="bot-id">SailorBot#0001</div>
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

<!-- 주문 조회 페이지 -->
<div id="pg-orders" class="page">
  <div class="inner">
    <div class="pg-title">주문 조회</div>
    <div class="pg-sub">디스코드 ID를 입력해 주문 내역을 확인하세요.</div>
    <div class="search-row">
      <input class="search-inp" type="text" placeholder="디스코드 ID 입력" id="dc-id">
      <button class="btn-fill" style="height:38px;padding:0 20px;font-size:13px" onclick="loadOrders()">조회</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr><th>주문번호</th><th>아이템</th><th>금액</th><th>상태</th><th>날짜</th></tr>
        </thead>
        <tbody id="order-rows">
          <tr><td colspan="5" style="text-align:center;padding:32px;color:var(--text3)">디스코드 ID를 입력하세요</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- 관리자 페이지 -->
<div id="pg-admin" class="page">
  <div class="inner inner-lg">
    <div class="pg-title">관리자 대시보드</div>
    <div class="pg-sub">판매 현황 및 주문 관리</div>
    <div class="a-grid">
      <div class="a-card"><div class="a-label">오늘 매출</div><div class="a-val">₩284,700</div></div>
      <div class="a-card"><div class="a-label">미처리 주문</div><div class="a-val">12</div></div>
      <div class="a-card"><div class="a-label">총 주문</div><div class="a-val">2,847</div></div>
      <div class="a-card"><div class="a-label">등록 아이템</div><div class="a-val">12</div></div>
    </div>
    <div class="sec-title">최근 주문</div>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>번호</th><th>디스코드 ID</th><th>아이템</th><th>금액</th><th>상태</th><th></th></tr></thead>
        <tbody id="admin-rows"></tbody>
      </table>
    </div>
    <div class="sec-title">봇 설정</div>
    <div class="a-card" style="display:flex;gap:10px;align-items:center;max-width:500px">
      <input class="search-inp" style="width:auto;flex:1" type="text" placeholder="Discord Webhook URL">
      <button class="btn-fill" style="height:38px;padding:0 18px;font-size:13px;white-space:nowrap" onclick="toast('웹훅이 저장되었습니다.')">저장</button>
    </div>
  </div>
</div>

<!-- 장바구니 -->
<div class="cart-ov" id="cart-ov" onclick="if(event.target===this)closeCart()">
  <div class="cart-drawer">
    <div class="d-head">
      <h2>장바구니</h2>
      <button class="close-btn" onclick="closeCart()">✕</button>
    </div>
    <div class="d-body" id="cart-body"></div>
    <div class="d-foot">
      <div class="d-total"><span>합계</span><span id="cart-total">₩ 0</span></div>
      <button class="order-btn" onclick="placeOrder()">
        <svg width="14" height="11" viewBox="0 0 16 12" fill="white"><path d="M13.545 1.022A13.23 13.23 0 0 0 10.237 0c-.147.265-.32.623-.438.907a12.22 12.22 0 0 0-3.598 0A10.54 10.54 0 0 0 5.76 0 13.258 13.258 0 0 0 2.448 1.025C.352 4.108-.216 7.115.068 10.08a13.312 13.312 0 0 0 4.048 2.05c.327-.444.617-.916.867-1.41a8.664 8.664 0 0 1-1.366-.658c.115-.084.227-.172.336-.261 2.632 1.217 5.487 1.217 8.088 0 .11.09.222.177.336.261-.435.258-.896.48-1.369.66.25.493.539.965.867 1.41a13.286 13.286 0 0 0 4.051-2.053c.332-3.462-.566-6.44-2.381-9.057Z"/></svg>
        디스코드로 주문하기
      </button>
      <div class="d-note">주문 후 디스코드에서 자동 처리됩니다.</div>
    </div>
  </div>
</div>

<!-- 관리자 모달 -->
<div class="modal-ov" id="modal-ov">
  <div class="modal">
    <h2>관리자 로그인</h2>
    <p>비밀번호를 입력하세요.</p>
    <input class="pw-inp" type="password" id="admin-pw" placeholder="비밀번호" onkeydown="if(event.key==='Enter')checkAdmin()">
    <div class="modal-btns">
      <button class="m-cancel" onclick="closeAdmin()">취소</button>
      <button class="m-ok" onclick="checkAdmin()">로그인</button>
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

const ADMIN_DATA = [
  {id:"#2847",user:"SailorKing#1234", item:"해왕의 창",   price:"₩28,000",st:"p"},
  {id:"#2846",user:"OceanRider#5678", item:"해적왕 스킨", price:"₩45,000",st:"ok"},
  {id:"#2845",user:"WaveRunner#9012", item:"번개 활",     price:"₩35,000",st:"ok"},
  {id:"#2844",user:"SeaBoss#3456",    item:"파도 스킨",   price:"₩22,000",st:"no"},
  {id:"#2843",user:"BluePirate#7890", item:"세일러 소드", price:"₩15,000",st:"ok"},
];

const ST_LABEL = {p:"처리중",ok:"완료",no:"취소"};
const ST_CLASS = {p:"st-p",ok:"st-ok",no:"st-no"};

const SVG = {
  weapon:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="m14.5 17.5-10 5 5-10 10-5-5 10zM12 12 7 7"/></svg>`,
  armor:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  accessory: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>`,
  skin:      `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="12" cy="10" r="3"/></svg>`,
};

let cart = [];
let curItems = [...ITEMS];

function renderGrid(list) {
  const g = document.getElementById('grid');
  if (!list.length) {
    g.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text3);font-size:13px">검색 결과가 없습니다.</div>`;
    return;
  }
  g.innerHTML = list.map(it => `
    <div class="item-card">
      <div class="item-img">
        ${it.tag ? `<div class="item-tag tag-${it.tag}">${it.tl}</div>` : ''}
        <div class="item-icon">${SVG[it.cat]}</div>
      </div>
      <div class="item-body">
        <div class="item-name">${it.name}</div>
        <div class="item-desc">${it.desc}</div>
        <div class="item-foot">
          <div class="item-price">₩${it.price.toLocaleString()} <span>원</span></div>
          <button class="add-btn" onclick="addToCart(${it.id})">담기</button>
        </div>
        ${it.stock <= 3 ? `<div class="item-stock">재고 ${it.stock}개</div>` : ''}
      </div>
    </div>
  `).join('');
}

function filterCat(cat, el) {
  document.querySelectorAll('.cat-item').forEach(b => b.classList.remove('on'));
  el.classList.add('on');
  curItems = cat === 'all' ? [...ITEMS] : ITEMS.filter(i => i.cat === cat);
  const name = el.childNodes[0].nodeValue.trim();
  document.getElementById('items-title').textContent = `${name} (${curItems.length})`;
  renderGrid(curItems);
}

function sortItems(v) {
  let s = [...curItems];
  if (v === 'asc') s.sort((a,b) => a.price - b.price);
  if (v === 'desc') s.sort((a,b) => b.price - a.price);
  renderGrid(s);
}

function applyFilter() {
  const mn = +document.getElementById('pmin').value || 0;
  const mx = +document.getElementById('pmax').value || Infinity;
  renderGrid(ITEMS.filter(i => i.price >= mn && i.price <= mx));
  toast('가격 필터가 적용되었습니다.');
}

function addToCart(id) {
  const it = ITEMS.find(i => i.id === id);
  const ex = cart.find(c => c.id === id);
  ex ? ex.qty++ : cart.push({...it, qty:1});
  updateCart();
  toast(`${it.name}이(가) 장바구니에 추가되었습니다.`);
}

function removeFromCart(id) { cart = cart.filter(c => c.id !== id); updateCart(); }

function updateCart() {
  const total = cart.reduce((s,c) => s + c.price * c.qty, 0);
  const qty   = cart.reduce((s,c) => s + c.qty, 0);
  document.getElementById('cart-count').textContent = qty;
  document.getElementById('cart-total').textContent = `₩ ${total.toLocaleString()}`;
  const el = document.getElementById('cart-body');
  if (!cart.length) {
    el.innerHTML = `<div class="cart-empty"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text3)" stroke-width="1.5"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg><p>장바구니가 비어있습니다.</p></div>`;
    return;
  }
  el.innerHTML = cart.map(c => `
    <div class="ci">
      <div class="ci-icon">${SVG[c.cat]}</div>
      <div style="flex:1">
        <div class="ci-name">${c.name} × ${c.qty}</div>
        <div class="ci-price">₩${(c.price * c.qty).toLocaleString()}</div>
      </div>
      <button class="ci-rm" onclick="removeFromCart(${c.id})">✕</button>
    </div>
  `).join('');
}

function openCart()  { document.getElementById('cart-ov').classList.add('on'); }
function closeCart() { document.getElementById('cart-ov').classList.remove('on'); }

function placeOrder() {
  if (!cart.length) { toast('장바구니가 비어있습니다.'); return; }
  const total = cart.reduce((s,c) => s + c.price * c.qty, 0);
  toast(`디스코드로 주문이 전송되었습니다. (₩${total.toLocaleString()})`);
  cart = []; updateCart(); closeCart();
}

function goTab(tab, el) {
  if (el) { document.querySelectorAll('.ntab').forEach(t => t.classList.remove('on')); el.classList.add('on'); }
  ['shop','orders','admin'].forEach(t => {
    document.getElementById('pg-'+t).className = t === tab ? 'page on' : 'page';
  });
}

function loadOrders() {
  const id = document.getElementById('dc-id').value.trim();
  if (!id) { toast('디스코드 ID를 입력하세요.'); return; }
  document.getElementById('order-rows').innerHTML = [
    {id:'#2840', item:'세일러 소드',     price:'₩15,000', st:'ok', date:'2025.04.10'},
    {id:'#2831', item:'크리스탈 목걸이', price:'₩8,000',  st:'p',  date:'2025.04.09'},
  ].map(r => `
    <tr>
      <td style="font-family:monospace;font-weight:600;color:var(--text)">${r.id}</td>
      <td>${r.item}</td>
      <td style="font-weight:700;color:var(--blue)">${r.price}</td>
      <td><span class="st ${ST_CLASS[r.st]}">${ST_LABEL[r.st]}</span></td>
      <td>${r.date}</td>
    </tr>
  `).join('');
  toast(`${id}의 주문 내역을 불러왔습니다.`);
}

function renderAdminRows() {
  document.getElementById('admin-rows').innerHTML = ADMIN_DATA.map(o => `
    <tr>
      <td style="font-family:monospace;font-weight:600;color:var(--text)">${o.id}</td>
      <td>${o.user}</td>
      <td>${o.item}</td>
      <td style="font-weight:700;color:var(--blue)">${o.price}</td>
      <td><span class="st ${ST_CLASS[o.st]}">${ST_LABEL[o.st]}</span></td>
      <td>${o.st === 'p' ? `<button class="add-btn" onclick="toast('${o.id} 완료 처리되었습니다.')">완료</button>` : '—'}</td>
    </tr>
  `).join('');
}

function openAdmin()  { document.getElementById('modal-ov').classList.add('on'); setTimeout(() => document.getElementById('admin-pw').focus(), 80); }
function closeAdmin() { document.getElementById('modal-ov').classList.remove('on'); document.getElementById('admin-pw').value = ''; }

function checkAdmin() {
  if (document.getElementById('admin-pw').value === 'admin1234') {
    closeAdmin(); goTab('admin'); renderAdminRows();
    toast('관리자 패널에 접속했습니다.');
  } else {
    toast('비밀번호가 올바르지 않습니다.');
    document.getElementById('admin-pw').value = '';
    document.getElementById('admin-pw').focus();
  }
}

let toastTimer;
function toast(msg) {
  const el = document.getElementById('toast-el');
  el.textContent = msg; el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), 2600);
}

renderGrid(ITEMS);
updateCart();

// 카운터
(function() {
  const el = document.getElementById('cnt');
  let n = 0;
  const id = setInterval(() => {
    n = Math.min(n + 55, 2847);
    el.textContent = n.toLocaleString();
    if (n >= 2847) clearInterval(id);
  }, 16);
})();
</script>
</body>
</html>
