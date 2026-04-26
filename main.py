<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OTT 최상급</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
/* ━━━━━━━━━━━━━━━━━━━━ CSS 변수 (라이트 기본) ━━━━━━━━━━━━━━━━━━━━ */
:root {
  --bg: #ffffff;
  --bg2: #f8fafc;
  --bg3: #f1f5f9;
  --card: #ffffff;
  --card-border: #e2e8f0;
  --text: #0f172a;
  --text2: #475569;
  --text3: #94a3b8;
  --nav-bg: rgba(255,255,255,0.95);
  --nav-border: #e2e8f0;
  --svc-bg: #ffffff;
  --svc-seg: #e8edf3;
  --svc-seg-ind: #ffffff;
  --svc-seg-btn: #64748b;
  --svc-seg-active: #0f172a;
  --svc-div: #e2e8f0;
  --svc-label: #94a3b8;
  --svc-price: #0f172a;
  --svc-period: #94a3b8;
  --svc-feat: #475569;
  --svc-chk-bg: #eff6ff;
  --faq-bg: #ffffff;
  --faq-border: #e2e8f0;
  --faq-text: #0f172a;
  --faq-body: #64748b;
  --faq-chevbg: #f1f5f9;
  --rv-bg: #ffffff;
  --rv-border: #e2e8f0;
  --rv-text: #0f172a;
  --rv-body: #475569;
  --hero-grad: linear-gradient(180deg,#ffffff 0%,#eff6ff 35%,#dbeafe 70%,#bfdbfe 100%);
  --stat-bg: #ffffff;
  --feat-bg: #ffffff;
  --section-bg: #ffffff;
  --footer-bg: var(--bg2);
  --svc-block-shadow: 0 2px 16px rgba(0,0,0,0.08);
}

/* 다크 모드 */
[data-theme="dark"] {
  --bg: #0a0a0a;
  --bg2: #111111;
  --bg3: #1a1a1a;
  --card: #1c1c1e;
  --card-border: #2c2c2e;
  --text: #f5f5f7;
  --text2: #aeaeb2;
  --text3: #636366;
  --nav-bg: rgba(10,10,10,0.95);
  --nav-border: #2c2c2e;
  --svc-bg: #1c1c1e;
  --svc-seg: #2c2c2e;
  --svc-seg-ind: #48484a;
  --svc-seg-btn: #636366;
  --svc-seg-active: #f5f5f7;
  --svc-div: #2c2c2e;
  --svc-label: #636366;
  --svc-price: #f5f5f7;
  --svc-period: #636366;
  --svc-feat: #aeaeb2;
  --svc-chk-bg: #2c2c2e;
  --faq-bg: #1c1c1e;
  --faq-border: #2c2c2e;
  --faq-text: #f5f5f7;
  --faq-body: #aeaeb2;
  --faq-chevbg: #2c2c2e;
  --rv-bg: #1c1c1e;
  --rv-border: #2c2c2e;
  --rv-text: #f5f5f7;
  --rv-body: #aeaeb2;
  --hero-grad: linear-gradient(180deg,#0a0a0a 0%,#0d1117 40%,#0d1a2d 100%);
  --stat-bg: #1c1c1e;
  --feat-bg: #1c1c1e;
  --section-bg: #0a0a0a;
  --footer-bg: var(--bg2);
  --svc-block-shadow: 0 2px 16px rgba(0,0,0,0.3);
}

/* ━━━ RESET ━━━ */
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html{scroll-behavior:smooth;}
body{
  font-family:'Noto Sans KR',-apple-system,BlinkMacSystemFont,sans-serif;
  background:var(--bg);color:var(--text);
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
  transition:background .25s,color .25s;
}

/* ━━━ NAV ━━━ */
nav{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:var(--nav-bg);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--nav-border);
  height:60px;padding:0 24px;
  display:flex;align-items:center;justify-content:space-between;
  transition:background .25s,border-color .25s;
}

/* ── 라이트 모드: 흰색 테마 컨트롤 ── */
.theme-ctrl{
  display:flex;align-items:center;
  background:#f1f5f9;
  border:1px solid #e2e8f0;
  border-radius:999px;
  padding:4px 5px;gap:2px;
}
.tcbtn{
  width:34px;height:34px;border-radius:999px;
  border:none;background:transparent;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:#64748b;
  transition:all .18s ease;flex-shrink:0;
}
.tcbtn:hover{color:#0f172a;}
.tcbtn.active{
  background:#ffffff;
  color:#0f172a;
  box-shadow:0 1px 4px rgba(0,0,0,0.12);
}

/* 다크 모드에서는 진한 배경 */
[data-theme="dark"] .theme-ctrl{
  background:#1e2230;
  border-color:transparent;
}
[data-theme="dark"] .tcbtn{
  color:#636366;
}
[data-theme="dark"] .tcbtn.active{
  background:#48484a;
  color:#f5f5f7;
  box-shadow:0 1px 4px rgba(0,0,0,0.3);
}

/* 오른쪽 햄버거 */
.ham{
  display:flex;flex-direction:column;gap:5px;padding:6px;
  background:none;border:none;cursor:default;opacity:0.4;pointer-events:none;
}
.ham span{display:block;width:22px;height:2px;background:var(--text);border-radius:2px;transition:background .25s;}

/* HERO */
.hero{
  min-height:100vh;
  background:var(--hero-grad);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:100px 24px 64px;text-align:center;
  transition:background .25s;
}
.badge-pill{
  display:inline-flex;align-items:center;gap:7px;
  background:rgba(239,246,255,0.9);border:1px solid #bfdbfe;
  padding:7px 16px;border-radius:999px;
  font-size:13px;font-weight:600;color:#2563eb;
  margin-bottom:22px;white-space:nowrap;
}
[data-theme="dark"] .badge-pill{background:rgba(30,41,59,0.8);border-color:#334155;}
.badge-pill svg{color:#2563eb;flex-shrink:0;}
.hero h1{font-size:clamp(28px,5.5vw,48px);font-weight:900;line-height:1.15;color:var(--text);letter-spacing:-0.8px;}
.hero h1 b{color:#2563eb;}
.hero-desc{font-size:15px;color:var(--text2);line-height:1.7;margin:14px auto 28px;max-width:380px;}
.cta-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:#2563eb;color:#fff;
  padding:15px 32px;border-radius:50px;
  font-size:16px;font-weight:700;border:none;cursor:pointer;
  text-decoration:none;font-family:inherit;
  box-shadow:0 2px 14px rgba(37,99,235,0.28);
  transition:transform .15s,box-shadow .15s;
}
.cta-btn:hover{transform:translateY(-2px);box-shadow:0 6px 22px rgba(37,99,235,0.36);}
.cta-btn svg{flex-shrink:0;}

/* STATS BAR */
.stats-bar{
  display:flex;align-items:center;
  background:var(--stat-bg);border:1px solid var(--card-border);border-radius:16px;
  margin-top:24px;width:100%;max-width:480px;overflow:hidden;
  box-shadow:0 1px 8px rgba(0,0,0,0.06);
  transition:background .25s,border-color .25s;
}
.stat-item{flex:1;padding:14px 8px;text-align:center;position:relative;}
.stat-item+.stat-item::before{content:'';position:absolute;left:0;top:20%;bottom:20%;width:1px;background:var(--card-border);}
.stat-num{font-size:17px;font-weight:900;color:var(--text);line-height:1;}
.stat-num em{font-size:12px;font-weight:700;color:#2563eb;font-style:normal;}
.stat-lbl{font-size:11px;color:var(--text3);margin-top:3px;font-weight:500;}

/* FEAT STACK */
.feat-stack{width:100%;max-width:480px;margin-top:16px;display:flex;flex-direction:column;gap:8px;}
.feat-row{
  background:var(--feat-bg);border:1px solid var(--card-border);border-radius:14px;
  padding:13px 16px;display:flex;align-items:center;gap:13px;text-align:left;
  box-shadow:0 1px 4px rgba(0,0,0,0.04);transition:background .25s,border-color .25s;
}
.ficon{width:36px;height:36px;border-radius:9px;background:#eff6ff;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;}
[data-theme="dark"] .ficon{background:#1e3a5f;}
.ftitle{font-size:14px;font-weight:700;color:var(--text);}
.fsub{font-size:12px;color:var(--text3);margin-top:1px;}

/* SECTION */
section{padding:64px 24px;background:var(--section-bg);transition:background .25s;}
.sc{text-align:center;margin-bottom:32px;}
.spill{display:inline-flex;align-items:center;gap:6px;border:1px solid #bfdbfe;background:#eff6ff;padding:6px 14px;border-radius:999px;font-size:12px;font-weight:600;color:#2563eb;margin-bottom:12px;white-space:nowrap;}
[data-theme="dark"] .spill{background:#1e3a5f;border-color:#2563eb;}
.spill svg{color:#2563eb;flex-shrink:0;}
.stitle{font-size:26px;font-weight:900;color:var(--text);margin-bottom:6px;letter-spacing:-0.3px;}
.sdesc{font-size:13px;color:var(--text2);line-height:1.65;}

/* SERVICES */
#services{background:var(--bg2);padding-bottom:72px;}
[data-theme="dark"] #services{background:var(--bg3);}
.svc-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:16px;}

/* 흰색 카드 스타일 */
.svc-block{
  border-radius:20px;overflow:hidden;
  background:var(--svc-bg);
  box-shadow:var(--svc-block-shadow);
  border:1px solid var(--card-border);
  transition:background .25s,box-shadow .2s,border-color .25s;
}
.svc-block:hover{box-shadow:0 8px 32px rgba(0,0,0,0.13);}
[data-theme="dark"] .svc-block:hover{box-shadow:0 8px 32px rgba(0,0,0,0.5);}

.svc-header{display:flex;align-items:center;gap:14px;padding:18px 18px 14px;background:transparent;}

/* ── 실제 앱 아이콘 스타일 ── */
.brand-icon{
  width:48px;height:48px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;overflow:hidden;
  box-shadow:0 2px 8px rgba(0,0,0,0.15);
}

/* 넷플릭스 아이콘 - 실제 앱과 유사하게 */
.brand-icon.nf-icon{
  background:#000000;
  position:relative;
}
/* 디스코드 아이콘 */
.brand-icon.dc-icon{background:linear-gradient(135deg,#5865F2 0%,#4752c4 100%);}
/* 스포티파이 아이콘 */
.brand-icon.sp-icon{background:linear-gradient(135deg,#1DB954 0%,#158a3e 100%);}
/* 유튜브 아이콘 */
.brand-icon.yt-icon{background:linear-gradient(135deg,#FF0000 0%,#cc0000 100%);}

.brand-name{font-size:16px;font-weight:800;color:var(--text);}
.brand-cat{font-size:11px;color:var(--text3);margin-top:2px;font-weight:500;}

/* segment */
.seg-wrap{padding:0 16px 14px;background:transparent;}
.seg-ctrl{
  display:flex;background:var(--svc-seg);border-radius:12px;padding:4px;
  position:relative;overflow:hidden;touch-action:pan-y;user-select:none;
  transition:background .25s;
}
.seg-btn{
  flex:1;padding:9px 4px;border:none;background:none;cursor:pointer;
  font-family:inherit;font-size:13px;font-weight:600;
  color:var(--svc-seg-btn);border-radius:9px;
  transition:color .15s;white-space:nowrap;
  position:relative;z-index:1;text-align:center;
}
.seg-btn.active{color:var(--svc-seg-active);}
.seg-indicator{
  position:absolute;top:4px;bottom:4px;
  background:var(--svc-seg-ind);border-radius:9px;
  transition:left .2s cubic-bezier(.4,0,.2,1),width .2s cubic-bezier(.4,0,.2,1);
  box-shadow:0 1px 4px rgba(0,0,0,0.12);pointer-events:none;
}
.seg-divider{height:1px;background:var(--svc-div);margin:0;transition:background .25s;}

/* option panel */
.opt-panel{display:none;padding:18px 18px 20px;animation:fadeUp .16s ease;background:transparent;}
.opt-panel.active{display:block;}
@keyframes fadeUp{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.opt-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;}
.opt-plan-label{font-size:11px;font-weight:700;color:var(--svc-label);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:4px;transition:color .25s;}
.opt-price{font-size:32px;font-weight:900;color:var(--svc-price);line-height:1;transition:color .25s;}
.opt-price span{font-size:13px;font-weight:500;color:var(--svc-period);margin-left:1px;}
.opt-period{font-size:12px;color:var(--svc-period);margin-top:4px;transition:color .25s;}
.opt-buy{
  padding:12px 20px;color:#fff;font-size:14px;font-weight:700;border:none;
  border-radius:11px;cursor:pointer;font-family:inherit;
  white-space:nowrap;flex-shrink:0;transition:opacity .15s,transform .12s;
}
.opt-buy:hover{opacity:.88;transform:translateY(-1px);}
.opt-divider{height:1px;background:var(--svc-div);margin-bottom:14px;transition:background .25s;}
.opt-feats{list-style:none;display:flex;flex-direction:column;gap:9px;}
.opt-feats li{display:flex;align-items:flex-start;gap:10px;font-size:13px;color:var(--svc-feat);font-weight:400;line-height:1.55;transition:color .25s;}
.chk{width:20px;height:20px;border-radius:6px;background:var(--svc-chk-bg);display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;transition:background .25s;}

/* 브랜드별 구매버튼 */
.netflix-buy{background:#000000;}
.discord-buy{background:#5865F2;}
.spotify-buy{background:#1DB954;}
.youtube-buy{background:#FF0000;}

/* 브랜드별 chk 색 */
.netflix-chk{color:#E50914;}
.discord-chk{color:#5865F2;}
.spotify-chk{color:#1DB954;}
.youtube-chk{color:#FF0000;}

/* REVIEWS */
#reviews{background:var(--section-bg);}
.rv-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:10px;}
.rv{border-radius:16px;padding:22px 20px;border:1.5px solid var(--rv-border);background:var(--rv-bg);transition:background .25s,border-color .25s;}
.rv-q{margin-bottom:8px;color:var(--text3);}
.rv-tit{font-size:15px;font-weight:700;color:var(--rv-text);margin-bottom:8px;}
.rv-txt{font-size:13px;line-height:1.75;color:var(--rv-body);margin-bottom:14px;}
.rv-bot{display:flex;align-items:center;justify-content:flex-end;gap:8px;border-top:1px solid var(--card-border);padding-top:12px;}
.rv-name{font-size:14px;font-weight:700;color:var(--rv-text);}
.rv-role{font-size:12px;color:var(--text3);}

/* FAQ */
#faq{background:var(--bg2);}
[data-theme="dark"] #faq{background:var(--bg3);}
.faq-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:8px;}
.fi{background:var(--faq-bg);border:1.5px solid var(--faq-border);border-radius:14px;overflow:hidden;transition:all .2s;}
.fi:hover{border-color:#93c5fd;box-shadow:0 2px 12px rgba(37,99,235,0.07);}
.fq{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;cursor:pointer;gap:12px;font-size:14px;font-weight:600;color:var(--faq-text);user-select:none;line-height:1.5;}
.fchev{width:30px;height:30px;border-radius:50%;background:var(--faq-chevbg);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--text3);transition:transform .3s cubic-bezier(.4,0,.2,1),background .2s,color .2s;}
.fi:hover .fchev,.fi.open .fchev{background:#eff6ff;color:#2563eb;}
[data-theme="dark"] .fi:hover .fchev,[data-theme="dark"] .fi.open .fchev{background:#1e3a5f;color:#60a5fa;}
.fi.open .fchev{transform:rotate(180deg);}
.fa{max-height:0;overflow:hidden;transition:max-height .4s cubic-bezier(.4,0,.2,1);}
.fi.open .fa{max-height:300px;}
.fa p{margin:0 20px 20px;padding-top:14px;font-size:14px;color:var(--faq-body);line-height:1.75;border-top:1px solid var(--faq-border);}
.faq-note{text-align:center;margin-top:20px;font-size:13px;color:var(--text3);}

/* FOOTER */
footer{background:var(--footer-bg);padding:36px 24px;text-align:center;transition:background .25s;}
.flinks{display:flex;justify-content:center;flex-wrap:wrap;margin-bottom:10px;}
.flinks a{font-size:12px;color:var(--text3);text-decoration:none;padding:0 12px;transition:color .15s;}
.flinks a:hover{color:var(--text2);}
.fcopy{font-size:12px;color:var(--text3);}

/* PC 반응형 */
@media(min-width:768px){
  nav{padding:0 40px;height:64px;}
  .hero{padding:120px 40px 80px;}
  .hero h1{font-size:clamp(36px,4.5vw,52px);}
  .hero-desc{font-size:16px;max-width:500px;}
  .stats-bar{max-width:560px;}
  .feat-stack{max-width:560px;flex-direction:row;flex-wrap:wrap;}
  .feat-row{flex:1;min-width:160px;}
  section{padding:80px 40px;}
  #services{padding-bottom:100px;}
  .svc-list{gap:16px;}
  .svc-block{border-radius:22px;}
  .svc-header{padding:22px 24px 16px;}
  .seg-wrap{padding:0 20px 16px;}
  .opt-panel{padding:20px 24px 24px;}
  .rv-list,.faq-list{max-width:800px;}
  .rv-txt{font-size:14px;}
  .fa p{font-size:14px;}
  .svc-list{display:grid;grid-template-columns:1fr 1fr;}
  .tcbtn{width:36px;height:36px;}
}
@media(min-width:1200px){
  .hero{max-width:1200px;margin:0 auto;}
  .svc-list{max-width:960px;margin:0 auto;}
  .rv-list,.faq-list{max-width:900px;}
}

/* ━━━ 햄버거 버튼 ━━━ */
.ham-btn{
  display:flex;flex-direction:column;justify-content:center;gap:5px;
  width:40px;height:40px;padding:8px;
  background:none;border:none;cursor:pointer;border-radius:10px;
  transition:background .15s;
}
.ham-btn:hover{background:var(--bg3);}
.ham-btn span{display:block;width:22px;height:2px;background:var(--text);border-radius:2px;transition:all .25s;}
.ham-btn.open span:nth-child(1){transform:translateY(7px) rotate(45deg);}
.ham-btn.open span:nth-child(2){opacity:0;transform:scaleX(0);}
.ham-btn.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg);}

/* ━━━ 로그인 버튼 ━━━ */
.login-btn{
  height:36px;padding:0 16px;
  background:#2563eb;color:#fff;
  border:none;border-radius:999px;
  font-size:13px;font-weight:700;cursor:pointer;
  font-family:inherit;transition:opacity .15s;
}
.login-btn:hover{opacity:.85;}

/* ━━━ 드롭다운 메뉴 ━━━ */
.drop-menu{
  position:fixed;top:60px;right:16px;z-index:99;
  background:var(--card);border:1px solid var(--card-border);
  border-radius:16px;padding:8px;
  box-shadow:0 8px 32px rgba(0,0,0,0.12);
  min-width:160px;
  display:none;
  flex-direction:column;gap:2px;
  animation:dropIn .15s ease;
}
.drop-menu.open{display:flex;}
@keyframes dropIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.drop-menu a{
  display:flex;align-items:center;gap:10px;
  padding:12px 14px;border-radius:10px;
  font-size:14px;font-weight:600;color:var(--text);
  text-decoration:none;transition:background .12s;
}
.drop-menu a:hover{background:var(--bg3);}
.drop-menu a svg{color:#2563eb;flex-shrink:0;}
@media(min-width:768px){
  .drop-menu{top:64px;right:24px;}
}

/* ━━━ 로그인 모달 ━━━ */
.modal-overlay{
  position:fixed;inset:0;z-index:200;
  background:rgba(0,0,0,0.45);
  display:none;align-items:center;justify-content:center;
  padding:20px;
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
}
.modal-overlay.open{display:flex;}
.modal-box{
  background:var(--bg);border-radius:24px;
  padding:32px 28px;width:100%;max-width:400px;
  position:relative;
  box-shadow:0 20px 60px rgba(0,0,0,0.2);
  animation:modalUp .2s ease;
}
@keyframes modalUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
[data-theme="dark"] .modal-box{border:1px solid var(--card-border);}
.modal-close{
  position:absolute;top:16px;right:16px;
  width:32px;height:32px;border-radius:50%;
  background:var(--bg3);border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:var(--text3);transition:background .15s,color .15s;
}
.modal-close:hover{background:var(--card-border);color:var(--text);}
.modal-logo{
  display:flex;align-items:center;gap:10px;
  margin-bottom:20px;
}
.modal-logo span{
  font-size:18px;font-weight:900;color:var(--text);
  letter-spacing:-0.3px;
}
.modal-title{
  font-size:26px;font-weight:900;color:var(--text);
  margin-bottom:6px;letter-spacing:-0.5px;
}
.modal-sub{
  font-size:13px;color:var(--text3);margin-bottom:24px;font-weight:500;
}
.modal-field{margin-bottom:14px;}
.modal-field label{
  display:block;font-size:13px;font-weight:700;
  color:var(--text);margin-bottom:8px;
}
.modal-field input{
  width:100%;padding:14px 16px;
  background:var(--bg2);border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;color:var(--text);
  font-family:inherit;outline:none;
  transition:border-color .15s,box-shadow .15s;
}
.modal-field input::placeholder{color:var(--text3);}
.modal-field input:focus{
  border-color:#2563eb;
  box-shadow:0 0 0 3px rgba(37,99,235,0.12);
}
.modal-send-btn{
  width:100%;padding:15px;margin-bottom:16px;
  background:#2563eb;color:#fff;
  border:none;border-radius:14px;
  font-size:15px;font-weight:700;cursor:pointer;
  font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:8px;
  transition:opacity .15s,transform .12s;
}
.modal-send-btn:hover{opacity:.88;transform:translateY(-1px);}
.modal-send-btn.disabled{background:#cbd5e1;cursor:not-allowed;transform:none;opacity:1;}
[data-theme="dark"] .modal-send-btn.disabled{background:#2c2c2e;color:#636366;}
.modal-divider{
  display:flex;align-items:center;gap:12px;
  margin-bottom:14px;color:var(--text3);font-size:12px;font-weight:500;
}
.modal-divider::before,.modal-divider::after{
  content:'';flex:1;height:1px;background:var(--card-border);
}
.modal-google-btn{
  width:100%;padding:14px;
  background:var(--bg);border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;font-weight:700;color:var(--text);
  cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:10px;
  transition:background .15s,border-color .15s;
}
.modal-google-btn:hover{background:var(--bg2);border-color:#94a3b8;}

/* ━━━ 로그인 유지 체크박스 ━━━ */
.modal-remember{margin-bottom:16px;}
.remember-label{
  display:flex;align-items:center;gap:10px;cursor:pointer;
  font-size:13px;color:var(--text2);user-select:none;
}
.remember-label input[type="checkbox"]{display:none;}
.remember-box{
  width:20px;height:20px;border-radius:6px;
  border:2px solid var(--card-border);
  background:var(--bg);flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
  transition:all .15s;
}
.remember-label input:checked + .remember-box{
  background:#2563eb;border-color:#2563eb;
}
.remember-label input:checked + .remember-box::after{
  content:'';display:block;
  width:5px;height:9px;
  border:2px solid #fff;border-top:none;border-left:none;
  transform:rotate(45deg) translateY(-1px);
}
.remember-text{font-weight:500;}

/* ━━━ 타이머 ━━━ */
.modal-timer{
  text-align:center;font-size:13px;
  color:var(--text3);margin-bottom:14px;font-weight:500;
}
.modal-timer span{color:#2563eb;font-weight:700;}

/* ━━━ 뒤로 버튼 ━━━ */
.modal-back{
  display:flex;align-items:center;gap:6px;
  background:none;border:none;cursor:pointer;
  font-size:13px;font-weight:600;color:var(--text3);
  font-family:inherit;padding:0;margin-bottom:16px;
  transition:color .15s;
}
.modal-back:hover{color:var(--text);}

/* ━━━ 재전송 버튼 ━━━ */
.modal-resend-btn{
  width:100%;padding:12px;
  background:none;border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;font-weight:600;
  color:var(--text2);cursor:pointer;font-family:inherit;
  transition:background .15s,border-color .15s;margin-top:10px;
}
.modal-resend-btn:hover{background:var(--bg2);border-color:#94a3b8;}

/* ━━━ 성공 아이콘 ━━━ */
.success-icon{
  width:72px;height:72px;border-radius:50%;
  background:#eff6ff;
  display:flex;align-items:center;justify-content:center;
  margin:0 auto;
}
[data-theme="dark"] .success-icon{background:#1e3a5f;}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <!-- 왼쪽: 밝기 토글 -->
  <div class="theme-ctrl" id="themeCtrl">
    <button class="tcbtn active" data-mode="light" onclick="setTheme('light',this)" title="라이트">
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"/>
        <path stroke-linecap="round" d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    </button>
    <button class="tcbtn" data-mode="dark" onclick="setTheme('dark',this)" title="다크">
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
      </svg>
    </button>
    <button class="tcbtn" data-mode="system" onclick="setTheme('system',this)" title="시스템">
      <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <path stroke-linecap="round" d="M8 21h8M12 17v4"/>
      </svg>
    </button>
  </div>
  <!-- 오른쪽: 메뉴 버튼 + 로그인 -->
  <div style="display:flex;align-items:center;gap:10px;">
    <button class="login-btn" onclick="openLogin()">로그인</button>
    <button class="ham-btn" id="hamBtn" onclick="toggleMenu()" aria-label="메뉴">
      <span></span><span></span><span></span>
    </button>
  </div>
</nav>

<!-- 드롭다운 메뉴 -->
<div class="drop-menu" id="dropMenu">
  <a href="#services" onclick="closeMenu()">
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
    플랜
  </a>
  <a href="#reviews" onclick="closeMenu()">
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
    후기
  </a>
  <a href="#faq" onclick="closeMenu()">
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17" stroke-linecap="round" stroke-width="2.5"/></svg>
    FAQ
  </a>
</div>

<!-- 로그인 모달 -->
<div class="modal-overlay" id="loginModal" onclick="handleOverlayClick(event)">
  <div class="modal-box">
    <button class="modal-close" onclick="closeLogin()">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
    </button>

    <!-- STEP 1: 이메일 입력 -->
    <div id="step1">
      <h2 class="modal-title">로그인</h2>
      <p class="modal-sub">이메일을 입력하여 시작하세요</p>
      <div class="modal-field">
        <label>이메일</label>
        <input type="email" id="loginEmail" placeholder="이메일을 입력하세요" autocomplete="email"
          onkeydown="if(event.key==='Enter')handleSendCode()"/>
      </div>
      <!-- 로그인 유지 -->
      <div class="modal-remember">
        <label class="remember-label">
          <input type="checkbox" id="rememberMe"/>
          <span class="remember-box"></span>
          <span class="remember-text">로그인 유지하기</span>
        </label>
      </div>
      <button class="modal-send-btn" id="sendCodeBtn" onclick="handleSendCode()">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        인증 코드 전송
      </button>
      <div class="modal-divider"><span>또는</span></div>
      <button class="modal-google-btn" onclick="handleGoogle()">
        <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
        Google로 로그인
      </button>
    </div>

    <!-- STEP 2: 인증코드 입력 -->
    <div id="step2" style="display:none;">
      <button class="modal-back" onclick="goBackStep1()">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
        뒤로
      </button>
      <h2 class="modal-title">인증 코드 입력</h2>
      <p class="modal-sub" id="codeSubText">이메일로 발송된 6자리 코드를 입력해주세요</p>
      <div class="modal-field">
        <label>인증 코드</label>
        <input type="text" id="verifyCode" placeholder="000000" maxlength="6"
          style="letter-spacing:8px;font-size:22px;font-weight:700;text-align:center;"
          oninput="this.value=this.value.replace(/[^0-9]/g,'')"
          onkeydown="if(event.key==='Enter')handleVerifyCode()"/>
      </div>
      <div class="modal-timer" id="codeTimer">유효 시간: <span id="timerCount">5:00</span></div>
      <button class="modal-send-btn" id="verifyBtn" onclick="handleVerifyCode()">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
        확인
      </button>
      <button class="modal-resend-btn" id="resendBtn" onclick="handleResend()">코드 재전송</button>
    </div>

    <!-- STEP 3: 로그인 성공 -->
    <div id="step3" style="display:none;text-align:center;padding:20px 0;">
      <div class="success-icon">
        <svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="#2563eb" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
      </div>
      <h2 class="modal-title" style="margin-top:16px;">로그인 완료!</h2>
      <p class="modal-sub" id="successEmail"></p>
      <button class="modal-send-btn" onclick="closeLogin()" style="margin-top:8px;">확인</button>
    </div>

  </div>
</div>

<!-- HERO -->
<section class="hero">
  <div class="badge-pill">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    365일 24시간 자동화 서비스
  </div>
  <h1>프리미엄 구독을<br><b>더 쉽게, 더 저렴하게</b></h1>
  <p class="hero-desc">넷플릭스, 유튜브, 스포티파이, 디스코드<br>프리미엄 구독을 최저가로 즉시 시작하세요.</p>
  <a href="#services" class="cta-btn">
    지금 바로 구매하기
    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
  </a>

  <div class="stats-bar">
    <div class="stat-item"><div class="stat-num">4.9<em>★</em></div><div class="stat-lbl">평균 평점</div></div>
    <div class="stat-item"><div class="stat-num">12,000<em>+</em></div><div class="stat-lbl">누적 이용자</div></div>
    <div class="stat-item"><div class="stat-num">5<em>분</em></div><div class="stat-lbl">평균 처리시간</div></div>
    <div class="stat-item"><div class="stat-num">365<em>일</em></div><div class="stat-lbl">연중무휴</div></div>
  </div>

  <div class="feat-stack">
    <div class="feat-row">
      <div class="ficon"><svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>
      <div><div class="ftitle">광고 없는 스트리밍</div><div class="fsub">넷플릭스·유튜브 광고 없이 시청</div></div>
    </div>
    <div class="feat-row">
      <div class="ficon"><svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg></div>
      <div><div class="ftitle">오프라인 다운로드</div><div class="fsub">스포티파이·넷플릭스 저장 후 시청</div></div>
    </div>
    <div class="feat-row">
      <div class="ficon"><svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2zm12-3c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2z"/></svg></div>
      <div><div class="ftitle">백그라운드 재생</div><div class="fsub">유튜브·스포티파이 화면 꺼도 재생</div></div>
    </div>
  </div>
</section>

<!-- SERVICES -->
<section id="services">
  <div class="sc">
    <div class="spill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>프리미엄 서비스</div>
    <h2 class="stitle">서비스별 요금 안내</h2>
    <p class="sdesc">플랜을 선택하고 원하는 옵션을 골라보세요</p>
  </div>
  <div class="svc-list">

    <!-- NETFLIX -->
    <div class="svc-block">
      <div class="svc-header">
        <!-- 실제 넷플릭스 앱 아이콘 스타일 SVG -->
        <div class="brand-icon nf-icon" style="background:#000;padding:0;overflow:hidden;">
          <img src="data:image/jpeg;base64,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" style="width:48px;height:48px;object-fit:cover;border-radius:12px;" alt="Netflix"/>
        </div>
        <div><div class="brand-name">넷플릭스</div><div class="brand-cat">영상 스트리밍</div></div>
      </div>
      <div class="seg-wrap"><div class="seg-ctrl" id="nf-seg">
        <div class="seg-indicator" id="nf-ind"></div>
        <button class="seg-btn active" data-idx="0">광고형</button>
        <button class="seg-btn" data-idx="1">스탠다드</button>
        <button class="seg-btn" data-idx="2">프리미엄</button>
        <button class="seg-btn" data-idx="3">가족</button>
      </div></div>
      <div class="seg-divider"></div>
      <div id="nf-panels">
        <div class="opt-panel active"><div class="opt-top"><div><div class="opt-plan-label">광고형 플랜</div><div class="opt-price">4,900<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy netflix-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>Full HD (1080p) 화질</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>동시 접속 2대</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>월 5시간 미만 광고 포함</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">스탠다드 플랜</div><div class="opt-price">7,900<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy netflix-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>Full HD (1080p) 화질</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>광고 없는 무제한 시청</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>동시 접속 2대</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>오프라인 다운로드</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">프리미엄 플랜</div><div class="opt-price">11,500<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy netflix-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>4K Ultra HD + HDR</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>광고 없는 무제한 시청</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>동시 접속 4대</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>Dolby Atmos 공간 음향</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">가족 플랜 (4인)</div><div class="opt-price">9,800<span>원/월</span></div><div class="opt-period">1개월 · 1인당 2,450원</div></div><button class="opt-buy netflix-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>최대 4개 독립 프로필</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>4K Ultra HD 화질</li><li><div class="chk netflix-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>광고 없는 무제한 시청</li></ul></div>
      </div>
    </div>

    <!-- DISCORD -->
    <div class="svc-block">
      <div class="svc-header">
        <div class="brand-icon dc-icon">
          <svg width="28" height="22" viewBox="0 0 71 55" fill="white">
            <path d="M60.1 4.9A58.55 58.55 0 0045.9 1a40.52 40.52 0 00-1.8 3.7 54.17 54.17 0 00-16.2 0A40.52 40.52 0 0026.1 1a58.29 58.29 0 00-14.2 3.9C1.74 19.4-.98 33.5.31 47.4a58.76 58.76 0 0017.9 9.1 44.88 44.88 0 003.9-6.3 38.33 38.33 0 01-6.1-2.9l1.4-1.1a41.9 41.9 0 0036.1 0l1.4 1.1a38.33 38.33 0 01-6.1 2.9 44.88 44.88 0 003.9 6.3 58.62 58.62 0 0017.9-9.1c1.5-15.7-2.4-29.7-10.4-42.5zM23.7 38.9c-3.5 0-6.4-3.2-6.4-7.1s2.8-7.1 6.4-7.1 6.4 3.2 6.4 7.1-2.9 7.1-6.4 7.1zm23.6 0c-3.5 0-6.4-3.2-6.4-7.1s2.8-7.1 6.4-7.1 6.4 3.2 6.4 7.1-2.9 7.1-6.4 7.1z"/>
          </svg>
        </div>
        <div><div class="brand-name">디스코드 니트로</div><div class="brand-cat">커뮤니티 · 게임</div></div>
      </div>
      <div class="seg-wrap"><div class="seg-ctrl" id="dc-seg">
        <div class="seg-indicator" id="dc-ind"></div>
        <button class="seg-btn active" data-idx="0">베이직</button>
        <button class="seg-btn" data-idx="1">니트로</button>
        <button class="seg-btn" data-idx="2">연간</button>
      </div></div>
      <div class="seg-divider"></div>
      <div id="dc-panels">
        <div class="opt-panel active"><div class="opt-top"><div><div class="opt-plan-label">니트로 베이직</div><div class="opt-price">3,300<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy discord-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>커스텀 이모지 사용</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>50MB 파일 업로드</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>커스텀 프로필 배너</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">니트로</div><div class="opt-price">5,500<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy discord-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>커스텀 이모지 · 스티커</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>500MB 파일 업로드</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>서버 부스트 2개 포함</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>HD 화상통화 1080p 60fps</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">연간 플랜</div><div class="opt-price">4,583<span>원/월</span></div><div class="opt-period">연간 결제 · 총 54,996원</div></div><button class="opt-buy discord-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>니트로 전체 혜택 포함</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>월 대비 17% 할인</li><li><div class="chk discord-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>끊김 없는 1년 혜택</li></ul></div>
      </div>
    </div>

    <!-- SPOTIFY -->
    <div class="svc-block">
      <div class="svc-header">
        <!-- 실제 스포티파이 앱 아이콘 스타일 SVG -->
        <div class="brand-icon sp-icon">
          <svg width="28" height="28" viewBox="0 0 168 168" xmlns="http://www.w3.org/2000/svg">
            <path fill="#fff" d="M84 0C37.6 0 0 37.6 0 84s37.6 84 84 84 84-37.6 84-84S130.4 0 84 0zm38.6 121.2c-1.5 2.5-4.8 3.3-7.3 1.7-20-12.2-45.2-15-74.8-8.2-2.9.7-5.7-1.1-6.4-3.9-.7-2.9 1.1-5.7 3.9-6.4 32.4-7.4 60.2-4.2 82.6 9.5 2.5 1.5 3.3 4.8 2 7.3zm10.3-22.9c-1.9 3.1-6 4.1-9.1 2.2-22.9-14.1-57.8-18.1-84.9-9.9-3.5 1-7.2-.9-8.2-4.4-1-3.5.9-7.2 4.4-8.2 31-9.4 69.5-4.9 95.6 11.3 3.1 1.8 4.1 5.9 2.2 9zm.9-23.8C108.9 56.6 67.7 55.3 43.5 62.8c-4.2 1.3-8.6-1.1-9.9-5.2-1.3-4.2 1.1-8.6 5.2-9.9C66.3 39 111.3 40.5 139 57.2c3.8 2.2 5 7.1 2.7 10.8-2.1 3.8-7 5-10.9 2.5z"/>
          </svg>
        </div>
        <div><div class="brand-name">스포티파이</div><div class="brand-cat">음악 스트리밍</div></div>
      </div>
      <div class="seg-wrap"><div class="seg-ctrl" id="sp-seg">
        <div class="seg-indicator" id="sp-ind"></div>
        <button class="seg-btn active" data-idx="0">개인</button>
        <button class="seg-btn" data-idx="1">듀오</button>
        <button class="seg-btn" data-idx="2">가족</button>
        <button class="seg-btn" data-idx="3">연간</button>
      </div></div>
      <div class="seg-divider"></div>
      <div id="sp-panels">
        <div class="opt-panel active"><div class="opt-top"><div><div class="opt-plan-label">개인 플랜</div><div class="opt-price">4,900<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy spotify-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>광고 없는 무제한 음악</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>오프라인 음악 다운로드</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>고음질 스트리밍</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">듀오 플랜</div><div class="opt-price">6,450<span>원/월</span></div><div class="opt-period">1개월 · 1인당 3,225원</div></div><button class="opt-buy spotify-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>2개 독립 프리미엄 계정</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>개인 플랜 전체 혜택</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">가족 플랜 (6인)</div><div class="opt-price">8,950<span>원/월</span></div><div class="opt-period">1개월 · 1인당 1,492원</div></div><button class="opt-buy spotify-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>최대 6개 독립 계정</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>개인 플랜 전체 혜택</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>가족 믹스 플레이리스트</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">연간 플랜</div><div class="opt-price">3,900<span>원/월</span></div><div class="opt-period">연간 결제 · 총 46,800원</div></div><button class="opt-buy spotify-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>개인 플랜 전체 혜택</li><li><div class="chk spotify-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>월 대비 약 20% 할인</li></ul></div>
      </div>
    </div>

    <!-- YOUTUBE -->
    <div class="svc-block">
      <div class="svc-header">
        <div class="brand-icon yt-icon">
          <svg width="30" height="22" viewBox="0 0 461 461" fill="white">
            <path d="M365.257 67.393H95.744C42.866 67.393 0 110.259 0 163.137v134.728c0 52.878 42.866 95.744 95.744 95.744h269.513c52.878 0 95.744-42.866 95.744-95.744V163.137c0-52.878-42.866-95.744-95.744-95.744zm-64.751 169.663l-126.06 60.123c-3.359 1.602-7.239-.847-7.239-4.568V168.607c0-3.774 3.982-6.22 7.348-4.514l126.06 63.881c3.748 1.899 3.683 7.274-.109 9.082z"/>
          </svg>
        </div>
        <div><div class="brand-name">유튜브 프리미엄</div><div class="brand-cat">동영상 · 음악</div></div>
      </div>
      <div class="seg-wrap"><div class="seg-ctrl" id="yt-seg">
        <div class="seg-indicator" id="yt-ind"></div>
        <button class="seg-btn active" data-idx="0">개인</button>
        <button class="seg-btn" data-idx="1">가족</button>
        <button class="seg-btn" data-idx="2">연간</button>
      </div></div>
      <div class="seg-divider"></div>
      <div id="yt-panels">
        <div class="opt-panel active"><div class="opt-top"><div><div class="opt-plan-label">개인 플랜</div><div class="opt-price">6,500<span>원/월</span></div><div class="opt-period">1개월 이용권</div></div><button class="opt-buy youtube-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>광고 없는 동영상 시청</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>백그라운드 재생</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>오프라인 동영상 저장</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>YouTube Music 포함</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">가족 플랜 (6인)</div><div class="opt-price">9,500<span>원/월</span></div><div class="opt-period">1개월 · 1인당 1,583원</div></div><button class="opt-buy youtube-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>최대 6명 가족 계정</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>개인 플랜 전체 혜택</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>YouTube Music 가족 포함</li></ul></div>
        <div class="opt-panel"><div class="opt-top"><div><div class="opt-plan-label">연간 플랜</div><div class="opt-price">5,400<span>원/월</span></div><div class="opt-period">연간 결제 · 총 64,800원</div></div><button class="opt-buy youtube-buy">구매하기</button></div><div class="opt-divider"></div><ul class="opt-feats"><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>개인 플랜 전체 혜택</li><li><div class="chk youtube-chk"><svg width="11" height="11" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></div>월 대비 약 17% 할인</li></ul></div>
      </div>
    </div>

  </div>
</section>

<!-- REVIEWS -->
<section id="reviews">
  <div class="sc">
    <div class="spill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>고객 후기</div>
    <h2 class="stitle">사용자 후기</h2>
    <p class="sdesc">빠른 고객 지원과 안정적인 서비스로 만족하는 사용자들</p>
  </div>
  <div class="rv-list">
    <div class="rv"><div class="rv-q"><svg width="18" height="14" viewBox="0 0 24 18" fill="currentColor"><path d="M0 18V10.5C0 4.725 3.675.975 11.025 0L12 1.8C9.225 2.7 7.575 5.025 7.5 7.5H11.25V18H0zm12.75 0V10.5C12.75 4.725 16.425.975 23.775 0L24.75 1.8c-2.775.9-4.425 3.225-4.5 5.7H24V18H12.75z"/></svg></div><div class="rv-tit">관리도 타 업체와 다르게 잘해주셔요</div><div class="rv-txt">저렴한 가격에 안전하고 편안하게 잘 쓰면서 보고있습니다! 관리도 타 업체와 다르게 잘해주시고, 응답도 빠르시고, 서비스도 깔끔합니다. 적극 추천드립니다!</div><div class="rv-bot"><div class="rv-name">현우님</div><div class="rv-role">프리미엄 이용자</div></div></div>
    <div class="rv"><div class="rv-q"><svg width="18" height="14" viewBox="0 0 24 18" fill="currentColor"><path d="M0 18V10.5C0 4.725 3.675.975 11.025 0L12 1.8C9.225 2.7 7.575 5.025 7.5 7.5H11.25V18H0zm12.75 0V10.5C12.75 4.725 16.425.975 23.775 0L24.75 1.8c-2.775.9-4.425 3.225-4.5 5.7H24V18H12.75z"/></svg></div><div class="rv-tit">신청 방법도 너무 간단하고 빨라요</div><div class="rv-txt">신청 방법도 너무 간단하고 빠르게 처리해주셔서 편하게 이용하는 중입니다. 문의 답장도 빠르시고 문제 생기면 바로바로 처리해주십니다. 저렴해서 앞으로도 계속 이용하려고요!</div><div class="rv-bot"><div class="rv-name">채은님</div><div class="rv-role">신규 이용자</div></div></div>
    <div class="rv"><div class="rv-q"><svg width="18" height="14" viewBox="0 0 24 18" fill="currentColor"><path d="M0 18V10.5C0 4.725 3.675.975 11.025 0L12 1.8C9.225 2.7 7.575 5.025 7.5 7.5H11.25V18H0zm12.75 0V10.5C12.75 4.725 16.425.975 23.775 0L24.75 1.8c-2.775.9-4.425 3.225-4.5 5.7H24V18H12.75z"/></svg></div><div class="rv-tit">결제 후 사후관리 깔끔합니다.</div><div class="rv-txt">저렴한 가격으로 프리미엄 상품 가입해서 정말 편하게 보고있습니다. 결제 후 사후관리 깔끔하구요. 반신반의하며 결제했는데 정말 잘 보고 있습니다. 감사합니다.</div><div class="rv-bot"><div class="rv-name">집중님</div><div class="rv-role">개인 플랜 이용자</div></div></div>
  </div>
</section>

<!-- FAQ -->
<section id="faq">
  <div class="sc">
    <div class="spill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17" stroke-linecap="round" stroke-width="2.5"/></svg>궁금한 점</div>
    <h2 class="stitle">자주 묻는 질문</h2>
    <p class="sdesc">궁금한 점이 있으시면 아래 질문들을 확인해보세요</p>
  </div>
  <div class="faq-list">
    <div class="fi"><div class="fq" onclick="toggleFi(this)">구매 후 언제 활성화되나요?<div class="fchev"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></div></div><div class="fa"><p>구매 후 자동 시스템을 통해 평균 5~10분 이내에 즉시 활성화됩니다. 365일 24시간 자동화 시스템으로 운영되어 별도의 대기 시간이 없습니다.</p></div></div>
    <div class="fi"><div class="fq" onclick="toggleFi(this)">평균 배송 기간은 어느정도 되나요?<div class="fchev"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></div></div><div class="fa"><p>결제 완료 후 자동 시스템을 통해 실시간으로 처리됩니다. 대부분의 경우 1~5분 이내에 계정 정보를 받아보실 수 있습니다.</p></div></div>
    <div class="fi"><div class="fq" onclick="toggleFi(this)">환불 규정과 방식이 궁금해요.<div class="fchev"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></div></div><div class="fa"><p>서비스 이용 시작 전 미사용 건에 한해 100% 환불이 가능합니다. 서비스 이용 후에는 이용 기간에 비례하여 환불이 진행됩니다.</p></div></div>
    <div class="fi"><div class="fq" onclick="toggleFi(this)">고객센터 운영 시간 및 상담 방법이 궁금해요.<div class="fchev"><svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></div></div><div class="fa"><p>24시간 365일 채널톡을 통해 상담이 가능합니다. 카카오톡 채널로 문의해 주세요.</p></div></div>
  </div>
  <p class="faq-note">추가로 궁금한 점이 있으시면 채널톡으로 문의해주세요.</p>
</section>

<!-- FOOTER -->
<footer>
  <div class="flinks"><a href="#">이용약관</a><a href="#">개인정보처리방침</a><a href="#">고객센터</a></div>
  <div class="fcopy">© 2025 OTT 최상급. All rights reserved.</div>
</footer>

<script>
/* ── 테마 ── */
function applyTheme(mode){
  const prefersDark = window.matchMedia('(prefers-color-scheme:dark)').matches;
  const isDark = mode==='dark' || (mode==='system' && prefersDark);
  document.documentElement.setAttribute('data-theme', isDark?'dark':'light');
}
function setTheme(mode, btn){
  document.querySelectorAll('.tcbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  applyTheme(mode);
  try{ localStorage.setItem('ott-theme', mode); }catch(e){}
}
// 초기 테마 적용
(function(){
  let saved='light';
  try{ saved=localStorage.getItem('ott-theme')||'light'; }catch(e){}
  const btn=document.querySelector(`.tcbtn[data-mode="${saved}"]`);
  if(btn){
    document.querySelectorAll('.tcbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
  }
  applyTheme(saved);
  window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{
    try{ if(localStorage.getItem('ott-theme')==='system') applyTheme('system'); }catch(e){}
  });
})();

/* ── Smooth scroll ── */
document.querySelectorAll('a[href^="#"]').forEach(a=>{
  a.addEventListener('click',e=>{
    const t=document.querySelector(a.getAttribute('href'));
    if(!t)return;e.preventDefault();
    window.scrollTo({top:t.offsetTop-64,behavior:'smooth'});
  });
});

/* ── Segment Control ── */
function initSeg(segId,panelId){
  const seg=document.getElementById(segId);
  if(!seg)return;
  const ind=seg.querySelector('.seg-indicator');
  const btns=seg.querySelectorAll('.seg-btn');
  const panelContainer=document.getElementById(panelId);
  if(!panelContainer)return;
  const panels=panelContainer.querySelectorAll('.opt-panel');
  let idx=0;

  function moveTo(i){
    if(i<0||i>=btns.length)return;
    idx=i;
    btns.forEach((b,j)=>b.classList.toggle('active',j===i));
    panels.forEach((p,j)=>p.classList.toggle('active',j===i));
    const b=btns[i];
    if(ind && b){
      ind.style.left=b.offsetLeft+'px';
      ind.style.width=b.offsetWidth+'px';
    }
  }

  // 초기 위치 설정 (렌더링 후)
  requestAnimationFrame(()=>{
    setTimeout(()=>moveTo(0),50);
  });

  btns.forEach((b,i)=>b.addEventListener('click',()=>moveTo(i)));

  // 스와이프 지원
  let sx=0;
  seg.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;},{passive:true});
  seg.addEventListener('touchend',e=>{
    const dx=e.changedTouches[0].clientX-sx;
    if(Math.abs(dx)>40){dx<0?moveTo(idx+1):moveTo(idx-1);}
  },{passive:true});
}

// 리사이즈 시 인디케이터 재조정
window.addEventListener('resize', ()=>{
  ['nf-seg','dc-seg','sp-seg','yt-seg'].forEach(id=>{
    const seg=document.getElementById(id);
    if(!seg)return;
    const activeBtn=seg.querySelector('.seg-btn.active');
    const ind=seg.querySelector('.seg-indicator');
    if(activeBtn&&ind){
      ind.style.left=activeBtn.offsetLeft+'px';
      ind.style.width=activeBtn.offsetWidth+'px';
    }
  });
});

initSeg('nf-seg','nf-panels');
initSeg('dc-seg','dc-panels');
initSeg('sp-seg','sp-panels');
initSeg('yt-seg','yt-panels');

/* ── FAQ ── */
function toggleFi(el){
  const item=el.parentElement;
  const was=item.classList.contains('open');
  document.querySelectorAll('.fi.open').forEach(i=>i.classList.remove('open'));
  if(!was)item.classList.add('open');
}

/* ── 햄버거 메뉴 ── */
function toggleMenu(){
  const btn=document.getElementById('hamBtn');
  const menu=document.getElementById('dropMenu');
  btn.classList.toggle('open');
  menu.classList.toggle('open');
}
function closeMenu(){
  document.getElementById('hamBtn').classList.remove('open');
  document.getElementById('dropMenu').classList.remove('open');
}
document.addEventListener('click',function(e){
  const btn=document.getElementById('hamBtn');
  const menu=document.getElementById('dropMenu');
  if(!btn||!menu)return;
  if(!btn.contains(e.target)&&!menu.contains(e.target)){
    btn.classList.remove('open');
    menu.classList.remove('open');
  }
});

/* ── 로그인 모달 ── */
function openLogin(){
  document.getElementById('loginModal').classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(()=>{ const inp=document.getElementById('loginEmail'); if(inp)inp.focus(); },200);
}
function closeLogin(){
  document.getElementById('loginModal').classList.remove('open');
  document.body.style.overflow='';
}
function handleOverlayClick(e){
  if(e.target===document.getElementById('loginModal')) closeLogin();
}
/* ── 서버 주소 (서버 실행 후 맞게 설정) ── */
const API = 'https://www.v0ut.com';

let timerInterval = null;

function showStep(n){
  document.getElementById('step1').style.display = n===1?'block':'none';
  document.getElementById('step2').style.display = n===2?'block':'none';
  document.getElementById('step3').style.display = n===3?'block':'none';
}

function goBackStep1(){
  clearInterval(timerInterval);
  showStep(1);
}

/* ── 인증코드 전송 ── */
async function handleSendCode(){
  const email = document.getElementById('loginEmail').value.trim();
  const btn = document.getElementById('sendCodeBtn');
  const emailInput = document.getElementById('loginEmail');

  if(!email || !email.includes('@')){
    emailInput.style.borderColor='#ef4444';
    emailInput.focus();
    setTimeout(()=>{ emailInput.style.borderColor=''; }, 1500);
    return;
  }

  btn.innerHTML = '전송 중...';
  btn.classList.add('disabled');
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/send-code`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({email})
    });
    const data = await res.json();

    if(!res.ok) throw new Error(data.detail || '전송 실패');

    // Step2로 이동
    document.getElementById('codeSubText').textContent = `${email} 으로 발송된 6자리 코드를 입력해주세요`;
    showStep(2);
    startTimer(300);
    document.getElementById('verifyCode').focus();

  } catch(err) {
    alert('오류: ' + err.message);
  } finally {
    btn.innerHTML = '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> 인증 코드 전송';
    btn.classList.remove('disabled');
    btn.disabled = false;
  }
}

/* ── 인증코드 검증 ── */
async function handleVerifyCode(){
  const email = document.getElementById('loginEmail').value.trim();
  const code = document.getElementById('verifyCode').value.trim();
  const btn = document.getElementById('verifyBtn');

  if(code.length !== 6){
    document.getElementById('verifyCode').style.borderColor='#ef4444';
    setTimeout(()=>{ document.getElementById('verifyCode').style.borderColor=''; }, 1500);
    return;
  }

  btn.textContent = '확인 중...';
  btn.classList.add('disabled');
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/verify-code`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({email, code})
    });
    const data = await res.json();

    if(!res.ok) throw new Error(data.detail || '인증 실패');

    clearInterval(timerInterval);

    // 로그인 유지 처리
    const remember = document.getElementById('rememberMe').checked;
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('ott_user', email);

    // Step3 성공 화면
    document.getElementById('successEmail').textContent = email + ' 로 로그인되었습니다.';
    showStep(3);

    // 네비게이션 로그인 버튼 → 이메일로 변경
    updateNavLogin(email);

  } catch(err) {
    alert('오류: ' + err.message);
  } finally {
    btn.innerHTML = '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg> 확인';
    btn.classList.remove('disabled');
    btn.disabled = false;
  }
}

/* ── 재전송 ── */
async function handleResend(){
  document.getElementById('verifyCode').value = '';
  clearInterval(timerInterval);
  showStep(1);
  await handleSendCode();
}

/* ── 타이머 ── */
function startTimer(seconds){
  clearInterval(timerInterval);
  let s = seconds;
  const el = document.getElementById('timerCount');
  function tick(){
    const m = Math.floor(s/60);
    const sec = s%60;
    if(el) el.textContent = `${m}:${sec.toString().padStart(2,'0')}`;
    if(s<=0){
      clearInterval(timerInterval);
      if(el) el.textContent = '만료됨';
      el.style.color='#ef4444';
    }
    s--;
  }
  tick();
  timerInterval = setInterval(tick, 1000);
}

/* ── 네비 로그인 버튼 상태 업데이트 ── */
function updateNavLogin(email){
  const btn = document.querySelector('.login-btn');
  if(btn){
    const name = email.split('@')[0];
    btn.textContent = name + ' ▾';
    btn.onclick = () => {
      if(confirm('로그아웃 하시겠습니까?')){
        localStorage.removeItem('ott_user');
        sessionStorage.removeItem('ott_user');
        btn.textContent = '로그인';
        btn.onclick = openLogin;
      }
    };
  }
}

/* ── 페이지 로드 시 로그인 유지 확인 ── */
(function checkSavedLogin(){
  const email = localStorage.getItem('ott_user') || sessionStorage.getItem('ott_user');
  if(email) updateNavLogin(email);
})();

function handleGoogle(){
  alert('Google 로그인은 준비 중입니다.');
}

/* ── 모달 열기/닫기 시 step 초기화 ── */
const _origOpenLogin = openLogin;
function openLogin(){
  showStep(1);
  document.getElementById('verifyCode') && (document.getElementById('verifyCode').value='');
  document.getElementById('loginModal').classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(()=>{ const inp=document.getElementById('loginEmail'); if(inp)inp.focus(); },200);
}

document.addEventListener('keydown',function(e){
  if(e.key==='Escape') closeLogin();
});
</script>

</body>
</html>
