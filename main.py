<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OTT 최상급</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
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

*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html{scroll-behavior:smooth;}
body{
  font-family:'Noto Sans KR',-apple-system,BlinkMacSystemFont,sans-serif;
  background:var(--bg);color:var(--text);
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
  transition:background .25s,color .25s;
}

/* NAV */
nav{
  position:fixed;top:0;left:0;right:0;z-index:100;
  background:var(--nav-bg);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid var(--nav-border);
  height:60px;padding:0 16px;
  display:flex;align-items:center;justify-content:space-between;
  transition:background .25s,border-color .25s;
}
.theme-ctrl{
  display:flex;align-items:center;
  background:#f1f5f9;border:1px solid #e2e8f0;
  border-radius:999px;padding:4px 5px;gap:2px;
}
.tcbtn{
  width:32px;height:32px;border-radius:999px;
  border:none;background:transparent;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  color:#64748b;transition:all .18s ease;flex-shrink:0;
}
.tcbtn:hover{color:#0f172a;}
.tcbtn.active{background:#ffffff;color:#0f172a;box-shadow:0 1px 4px rgba(0,0,0,0.12);}
[data-theme="dark"] .theme-ctrl{background:#1e2230;border-color:transparent;}
[data-theme="dark"] .tcbtn{color:#636366;}
[data-theme="dark"] .tcbtn.active{background:#48484a;color:#f5f5f7;box-shadow:0 1px 4px rgba(0,0,0,0.3);}

.login-btn{
  height:36px;padding:0 16px;
  background:#2563eb;color:#fff;
  border:none;border-radius:999px;
  font-size:13px;font-weight:700;cursor:pointer;
  font-family:inherit;transition:opacity .15s;
  white-space:nowrap;
}
.login-btn:hover{opacity:.85;}

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

/* DROPDOWN */
.drop-menu{
  position:fixed;top:60px;right:12px;z-index:99;
  background:var(--card);border:1px solid var(--card-border);
  border-radius:16px;padding:8px;
  box-shadow:0 8px 32px rgba(0,0,0,0.12);
  min-width:160px;display:none;
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

/* HERO */
.hero{
  min-height:100vh;
  background:var(--hero-grad);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:90px 20px 60px;text-align:center;
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
.hero h1{font-size:clamp(26px,6vw,48px);font-weight:900;line-height:1.15;color:var(--text);letter-spacing:-0.8px;}
.hero h1 b{color:#2563eb;}
.hero-desc{font-size:15px;color:var(--text2);line-height:1.7;margin:14px auto 28px;max-width:340px;}
.cta-btn{
  display:inline-flex;align-items:center;gap:8px;
  background:#2563eb;color:#fff;
  padding:14px 28px;border-radius:50px;
  font-size:15px;font-weight:700;border:none;cursor:pointer;
  text-decoration:none;font-family:inherit;
  box-shadow:0 2px 14px rgba(37,99,235,0.28);
  transition:transform .15s,box-shadow .15s;
}
.cta-btn:hover{transform:translateY(-2px);box-shadow:0 6px 22px rgba(37,99,235,0.36);}

/* STATS */
.stats-bar{
  display:flex;align-items:center;
  background:var(--stat-bg);border:1px solid var(--card-border);border-radius:16px;
  margin-top:24px;width:100%;max-width:480px;overflow:hidden;
  box-shadow:0 1px 8px rgba(0,0,0,0.06);
  transition:background .25s,border-color .25s;
}
.stat-item{flex:1;padding:12px 6px;text-align:center;position:relative;}
.stat-item+.stat-item::before{content:'';position:absolute;left:0;top:20%;bottom:20%;width:1px;background:var(--card-border);}
.stat-num{font-size:16px;font-weight:900;color:var(--text);line-height:1;}
.stat-num em{font-size:11px;font-weight:700;color:#2563eb;font-style:normal;}
.stat-lbl{font-size:10px;color:var(--text3);margin-top:3px;font-weight:500;}

/* FEAT */
.feat-stack{width:100%;max-width:480px;margin-top:16px;display:flex;flex-direction:column;gap:8px;}
.feat-row{
  background:var(--feat-bg);border:1px solid var(--card-border);border-radius:14px;
  padding:12px 14px;display:flex;align-items:center;gap:12px;text-align:left;
  box-shadow:0 1px 4px rgba(0,0,0,0.04);transition:background .25s,border-color .25s;
}
.ficon{width:34px;height:34px;border-radius:9px;background:#eff6ff;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;}
[data-theme="dark"] .ficon{background:#1e3a5f;}
.ftitle{font-size:13px;font-weight:700;color:var(--text);}
.fsub{font-size:11px;color:var(--text3);margin-top:1px;}

/* SECTION */
section{padding:60px 20px;background:var(--section-bg);transition:background .25s;}
.sc{text-align:center;margin-bottom:28px;}
.spill{display:inline-flex;align-items:center;gap:6px;border:1px solid #bfdbfe;background:#eff6ff;padding:6px 14px;border-radius:999px;font-size:12px;font-weight:600;color:#2563eb;margin-bottom:12px;white-space:nowrap;}
[data-theme="dark"] .spill{background:#1e3a5f;border-color:#2563eb;}
.stitle{font-size:24px;font-weight:900;color:var(--text);margin-bottom:6px;letter-spacing:-0.3px;}
.sdesc{font-size:13px;color:var(--text2);line-height:1.65;}

/* SERVICES */
#services{background:var(--bg2);}
[data-theme="dark"] #services{background:var(--bg3);}
.svc-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:14px;}

.svc-block{
  border-radius:18px;overflow:hidden;
  background:var(--svc-bg);
  box-shadow:var(--svc-block-shadow);
  border:1px solid var(--card-border);
  transition:background .25s,box-shadow .2s,border-color .25s;
}
.svc-block:hover{box-shadow:0 8px 32px rgba(0,0,0,0.13);}
[data-theme="dark"] .svc-block:hover{box-shadow:0 8px 32px rgba(0,0,0,0.5);}

.svc-header{display:flex;align-items:center;gap:14px;padding:16px 16px 12px;}
.brand-icon{
  width:48px;height:48px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;overflow:hidden;
  box-shadow:0 2px 8px rgba(0,0,0,0.15);
}
/* Netflix 아이콘 - SVG로 교체 (base64 제거) */
.brand-icon.nf-icon{background:#000;}
.brand-icon.dc-icon{background:linear-gradient(135deg,#5865F2 0%,#4752c4 100%);}
.brand-icon.sp-icon{background:linear-gradient(135deg,#1DB954 0%,#158a3e 100%);}
.brand-icon.yt-icon{background:linear-gradient(135deg,#FF0000 0%,#cc0000 100%);}
.brand-name{font-size:15px;font-weight:800;color:var(--text);}
.brand-cat{font-size:11px;color:var(--text3);margin-top:2px;font-weight:500;}

/* SEGMENT */
.seg-wrap{padding:0 14px 12px;}
.seg-ctrl{
  display:flex;background:var(--svc-seg);border-radius:12px;padding:4px;
  position:relative;overflow:hidden;touch-action:pan-y;user-select:none;
  transition:background .25s;
}
.seg-btn{
  flex:1;padding:8px 4px;border:none;background:none;cursor:pointer;
  font-family:inherit;font-size:12px;font-weight:600;
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
.opt-panel{display:none;padding:16px 16px 18px;animation:fadeUp .16s ease;}
.opt-panel.active{display:block;}
@keyframes fadeUp{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.opt-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;}
.opt-plan-label{font-size:11px;font-weight:700;color:var(--svc-label);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:4px;}
.opt-price{font-size:28px;font-weight:900;color:var(--svc-price);line-height:1;}
.opt-price span{font-size:13px;font-weight:500;color:var(--svc-period);margin-left:1px;}
.opt-period{font-size:12px;color:var(--svc-period);margin-top:4px;}
.opt-buy{
  padding:11px 18px;color:#fff;font-size:13px;font-weight:700;border:none;
  border-radius:11px;cursor:pointer;font-family:inherit;
  white-space:nowrap;flex-shrink:0;transition:opacity .15s,transform .12s;
}
.opt-buy:hover{opacity:.88;transform:translateY(-1px);}
.opt-divider{height:1px;background:var(--svc-div);margin-bottom:14px;}
.opt-feats{list-style:none;display:flex;flex-direction:column;gap:8px;}
.opt-feats li{display:flex;align-items:flex-start;gap:10px;font-size:13px;color:var(--svc-feat);font-weight:400;line-height:1.55;}
.chk{width:20px;height:20px;border-radius:6px;background:var(--svc-chk-bg);display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;}
.netflix-buy{background:#E50914;}
.discord-buy{background:#5865F2;}
.spotify-buy{background:#1DB954;}
.youtube-buy{background:#FF0000;}
.netflix-chk{color:#E50914;}
.discord-chk{color:#5865F2;}
.spotify-chk{color:#1DB954;}
.youtube-chk{color:#FF0000;}

/* REVIEWS */
#reviews{background:var(--section-bg);}
.rv-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:10px;}
.rv{border-radius:16px;padding:20px;border:1.5px solid var(--rv-border);background:var(--rv-bg);transition:background .25s,border-color .25s;}
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
.fq{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;cursor:pointer;gap:12px;font-size:14px;font-weight:600;color:var(--faq-text);user-select:none;line-height:1.5;}
.fchev{width:28px;height:28px;border-radius:50%;background:var(--faq-chevbg);flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--text3);transition:transform .3s cubic-bezier(.4,0,.2,1),background .2s,color .2s;}
.fi:hover .fchev,.fi.open .fchev{background:#eff6ff;color:#2563eb;}
[data-theme="dark"] .fi:hover .fchev,[data-theme="dark"] .fi.open .fchev{background:#1e3a5f;color:#60a5fa;}
.fi.open .fchev{transform:rotate(180deg);}
.fa{max-height:0;overflow:hidden;transition:max-height .4s cubic-bezier(.4,0,.2,1);}
.fi.open .fa{max-height:300px;}
.fa p{margin:0 18px 18px;padding-top:12px;font-size:14px;color:var(--faq-body);line-height:1.75;border-top:1px solid var(--faq-border);}
.faq-note{text-align:center;margin-top:20px;font-size:13px;color:var(--text3);}

/* FOOTER */
footer{background:var(--footer-bg);padding:32px 20px;text-align:center;transition:background .25s;}
.flinks{display:flex;justify-content:center;flex-wrap:wrap;margin-bottom:10px;}
.flinks a{font-size:12px;color:var(--text3);text-decoration:none;padding:0 12px;transition:color .15s;}
.flinks a:hover{color:var(--text2);}
.fcopy{font-size:12px;color:var(--text3);}

/* 로그인 모달 */
.modal-overlay{
  position:fixed;inset:0;z-index:200;
  background:rgba(0,0,0,0.5);
  display:none;align-items:center;justify-content:center;
  padding:20px;
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
}
.modal-overlay.open{display:flex;}
.modal-box{
  background:var(--bg);border-radius:24px;
  padding:28px 24px;width:100%;max-width:400px;
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
.modal-title{font-size:24px;font-weight:900;color:var(--text);margin-bottom:6px;letter-spacing:-0.5px;}
.modal-sub{font-size:13px;color:var(--text3);margin-bottom:22px;font-weight:500;}
.modal-field{margin-bottom:14px;}
.modal-field label{display:block;font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px;}
.modal-field input{
  width:100%;padding:13px 15px;
  background:var(--bg2);border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;color:var(--text);
  font-family:inherit;outline:none;
  transition:border-color .15s,box-shadow .15s;
}
.modal-field input::placeholder{color:var(--text3);}
.modal-field input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,0.12);}
.modal-send-btn{
  width:100%;padding:14px;margin-bottom:14px;
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
.modal-divider{display:flex;align-items:center;gap:12px;margin-bottom:14px;color:var(--text3);font-size:12px;font-weight:500;}
.modal-divider::before,.modal-divider::after{content:'';flex:1;height:1px;background:var(--card-border);}
.modal-google-btn{
  width:100%;padding:13px;
  background:var(--bg);border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;font-weight:700;color:var(--text);
  cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center;gap:10px;
  transition:background .15s,border-color .15s;
}
.modal-google-btn:hover{background:var(--bg2);border-color:#94a3b8;}
.modal-remember{margin-bottom:14px;}
.remember-label{display:flex;align-items:center;gap:10px;cursor:pointer;font-size:13px;color:var(--text2);user-select:none;}
.remember-label input[type="checkbox"]{display:none;}
.remember-box{
  width:20px;height:20px;border-radius:6px;
  border:2px solid var(--card-border);background:var(--bg);flex-shrink:0;
  display:flex;align-items:center;justify-content:center;transition:all .15s;
}
.remember-label input:checked + .remember-box{background:#2563eb;border-color:#2563eb;}
.remember-label input:checked + .remember-box::after{
  content:'';display:block;width:5px;height:9px;
  border:2px solid #fff;border-top:none;border-left:none;
  transform:rotate(45deg) translateY(-1px);
}
.modal-timer{text-align:center;font-size:13px;color:var(--text3);margin-bottom:14px;font-weight:500;}
.modal-timer span{color:#2563eb;font-weight:700;}
.modal-back{
  display:flex;align-items:center;gap:6px;
  background:none;border:none;cursor:pointer;
  font-size:13px;font-weight:600;color:var(--text3);
  font-family:inherit;padding:0;margin-bottom:16px;transition:color .15s;
}
.modal-back:hover{color:var(--text);}
.modal-resend-btn{
  width:100%;padding:12px;
  background:none;border:1.5px solid var(--card-border);
  border-radius:14px;font-size:14px;font-weight:600;
  color:var(--text2);cursor:pointer;font-family:inherit;
  transition:background .15s,border-color .15s;margin-top:10px;
}
.modal-resend-btn:hover{background:var(--bg2);border-color:#94a3b8;}
.success-icon{
  width:72px;height:72px;border-radius:50%;
  background:#eff6ff;
  display:flex;align-items:center;justify-content:center;
  margin:0 auto;
}
[data-theme="dark"] .success-icon{background:#1e3a5f;}

/* PC 반응형 */
@media(min-width:768px){
  nav{padding:0 32px;height:64px;}
  .tcbtn{width:36px;height:36px;}
  .drop-menu{top:64px;right:24px;}
  .hero{padding:120px 40px 80px;}
  .hero h1{font-size:clamp(36px,4.5vw,52px);}
  .hero-desc{font-size:16px;max-width:480px;}
  .stats-bar{max-width:560px;}
  .feat-stack{max-width:560px;flex-direction:row;flex-wrap:wrap;}
  .feat-row{flex:1;min-width:160px;}
  section{padding:80px 40px;}
  .svc-list{gap:16px;}
  .svc-block{border-radius:22px;}
  .svc-header{padding:22px 24px 16px;}
  .seg-wrap{padding:0 20px 16px;}
  .opt-panel{padding:20px 24px 24px;}
  .rv-list,.faq-list{max-width:800px;}
}
@media(min-width:1200px){
  .svc-list{max-width:960px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;}
  .rv-list,.faq-list{max-width:900px;}
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="theme-ctrl" id="themeCtrl">
    <button class="tcbtn active" data-mode="light" onclick="setTheme('light',this)" title="라이트">
      <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"/>
        <path stroke-linecap="round" d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    </button>
    <button class="tcbtn" data-mode="dark" onclick="setTheme('dark',this)" title="다크">
      <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
      </svg>
    </button>
    <button class="tcbtn" data-mode="system" onclick="setTheme('system',this)" title="시스템">
      <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <path stroke-linecap="round" d="M8 21h8M12 17v4"/>
      </svg>
    </button>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <button class="login-btn" onclick="openLogin()">로그인</button>
    <button class="ham-btn" id="hamBtn" onclick="toggleMenu()" aria-label="메뉴">
      <span></span><span></span><span></span>
    </button>
  </div>
</nav>

<!-- 드롭다운 -->
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

    <!-- STEP 1 -->
    <div id="step1">
      <h2 class="modal-title">로그인</h2>
      <p class="modal-sub">이메일을 입력하여 시작하세요</p>
      <div class="modal-field">
        <label>이메일</label>
        <input type="email" id="loginEmail" placeholder="이메일을 입력하세요" autocomplete="email"
          onkeydown="if(event.key==='Enter')handleSendCode()"/>
      </div>
      <div class="modal-remember">
        <label class="remember-label">
          <input type="checkbox" id="rememberMe"/>
          <span class="remember-box"></span>
          <span>로그인 유지하기</span>
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

    <!-- STEP 2 -->
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
      <button class="modal-resend-btn" onclick="handleResend()">코드 재전송</button>
    </div>

    <!-- STEP 3 -->
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
        <!-- Netflix N 아이콘 (실제 로고 스타일) -->
        <div class="brand-icon nf-icon">
          <svg width="30" height="36" viewBox="0 0 100 120" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="nfgrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#b81c1c"/>
                <stop offset="50%" style="stop-color:#e50914"/>
                <stop offset="100%" style="stop-color:#8b0000"/>
              </linearGradient>
            </defs>
            <rect x="4" y="0" width="22" height="120" fill="url(#nfgrad)"/>
            <rect x="74" y="0" width="22" height="120" fill="url(#nfgrad)"/>
            <polygon points="4,0 26,0 96,120 74,120" fill="#e50914"/>
            <polygon points="26,0 46,0 74,60 54,60" fill="#8b0000" opacity="0.5"/>
          </svg>
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
    <div class="rv"><div class="rv-q"><svg width="18" height="14" viewBox="0 0 24 18" fill="currentColor"><path d="M0 18V10.5C0 4.725 3.675.975 11.025 0L12 1.8C9.225 2.7 7.575 5.025 7.5 7.5H11.25V18H0zm12.75 0V10.5C12.75 4.725 16.425.975 23.775 0L24.75 1.8c-2.775.9-4.425 3.225-4.5 5.7H24V18H12.75z"/></svg></div><div class="rv-tit">신청 방법도 너무 간단하고 빨라요</div><div class="rv-txt">신청 방법도 너무 간단하고 빠르게 처리해주셔서 편하게 이용하는 중입니다. 문의 답장도 빠르시고 문제 생기면 바로바로 처리해주십니다.</div><div class="rv-bot"><div class="rv-name">채은님</div><div class="rv-role">신규 이용자</div></div></div>
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

<footer>
  <div class="flinks"><a href="#">이용약관</a><a href="#">개인정보처리방침</a><a href="#">고객센터</a></div>
  <div class="fcopy">© 2025 OTT 최상급. All rights reserved.</div>
</footer>

<script>
/* 테마 */
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
(function(){
  let saved='light';
  try{ saved=localStorage.getItem('ott-theme')||'light'; }catch(e){}
  const btn=document.querySelector(`.tcbtn[data-mode="${saved}"]`);
  if(btn){ document.querySelectorAll('.tcbtn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); }
  applyTheme(saved);
  window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{
    try{ if(localStorage.getItem('ott-theme')==='system') applyTheme('system'); }catch(e){}
  });
})();

/* Smooth scroll */
document.querySelectorAll('a[href^="#"]').forEach(a=>{
  a.addEventListener('click',e=>{
    const t=document.querySelector(a.getAttribute('href'));
    if(!t)return;e.preventDefault();
    const navH = document.querySelector('nav').offsetHeight;
    window.scrollTo({top:t.offsetTop-navH,behavior:'smooth'});
  });
});

/* Segment Control */
function initSeg(segId, panelId){
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
    if(ind&&b){ ind.style.left=b.offsetLeft+'px'; ind.style.width=b.offsetWidth+'px'; }
  }
  requestAnimationFrame(()=>{ setTimeout(()=>moveTo(0),50); });
  btns.forEach((b,i)=>b.addEventListener('click',()=>moveTo(i)));

  let sx=0;
  seg.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;},{passive:true});
  seg.addEventListener('touchend',e=>{
    const dx=e.changedTouches[0].clientX-sx;
    if(Math.abs(dx)>40){dx<0?moveTo(idx+1):moveTo(idx-1);}
  },{passive:true});
}

window.addEventListener('resize',()=>{
  ['nf-seg','dc-seg','sp-seg','yt-seg'].forEach(id=>{
    const seg=document.getElementById(id);
    if(!seg)return;
    const activeBtn=seg.querySelector('.seg-btn.active');
    const ind=seg.querySelector('.seg-indicator');
    if(activeBtn&&ind){ ind.style.left=activeBtn.offsetLeft+'px'; ind.style.width=activeBtn.offsetWidth+'px'; }
  });
});

initSeg('nf-seg','nf-panels');
initSeg('dc-seg','dc-panels');
initSeg('sp-seg','sp-panels');
initSeg('yt-seg','yt-panels');

/* FAQ */
function toggleFi(el){
  const item=el.parentElement;
  const was=item.classList.contains('open');
  document.querySelectorAll('.fi.open').forEach(i=>i.classList.remove('open'));
  if(!was)item.classList.add('open');
}

/* 햄버거 */
function toggleMenu(){
  document.getElementById('hamBtn').classList.toggle('open');
  document.getElementById('dropMenu').classList.toggle('open');
}
function closeMenu(){
  document.getElementById('hamBtn').classList.remove('open');
  document.getElementById('dropMenu').classList.remove('open');
}
document.addEventListener('click',function(e){
  const btn=document.getElementById('hamBtn');
  const menu=document.getElementById('dropMenu');
  if(!btn||!menu)return;
  if(!btn.contains(e.target)&&!menu.contains(e.target)){ btn.classList.remove('open'); menu.classList.remove('open'); }
});

/* 로그인 모달 */
const API = 'https://www.v0ut.com';
let timerInterval = null;

function showStep(n){
  document.getElementById('step1').style.display = n===1?'block':'none';
  document.getElementById('step2').style.display = n===2?'block':'none';
  document.getElementById('step3').style.display = n===3?'block':'none';
}
function openLogin(){
  showStep(1);
  const vc = document.getElementById('verifyCode');
  if(vc) vc.value='';
  document.getElementById('loginModal').classList.add('open');
  document.body.style.overflow='hidden';
  setTimeout(()=>{ const inp=document.getElementById('loginEmail'); if(inp)inp.focus(); },200);
}
function closeLogin(){
  document.getElementById('loginModal').classList.remove('open');
  document.body.style.overflow='';
  clearInterval(timerInterval);
}
function handleOverlayClick(e){
  if(e.target===document.getElementById('loginModal')) closeLogin();
}
function goBackStep1(){
  clearInterval(timerInterval);
  showStep(1);
}

async function handleSendCode(){
  const email = document.getElementById('loginEmail').value.trim();
  const btn = document.getElementById('sendCodeBtn');
  const emailInput = document.getElementById('loginEmail');
  if(!email || !email.includes('@')){
    emailInput.style.borderColor='#ef4444';
    emailInput.focus();
    setTimeout(()=>{ emailInput.style.borderColor=''; },1500);
    return;
  }
  btn.innerHTML = '전송 중...';
  btn.classList.add('disabled');
  btn.disabled = true;
  try {
    const res = await fetch(`${API}/send-code`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email})
    });
    const data = await res.json();
    if(!res.ok) throw new Error(data.detail||'전송 실패');
    document.getElementById('codeSubText').textContent = `${email} 으로 발송된 6자리 코드를 입력해주세요`;
    showStep(2);
    startTimer(300);
    document.getElementById('verifyCode').focus();
  } catch(err) {
    alert('오류: '+err.message);
  } finally {
    btn.innerHTML = '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> 인증 코드 전송';
    btn.classList.remove('disabled');
    btn.disabled = false;
  }
}

async function handleVerifyCode(){
  const email = document.getElementById('loginEmail').value.trim();
  const code = document.getElementById('verifyCode').value.trim();
  const btn = document.getElementById('verifyBtn');
  if(code.length!==6){
    document.getElementById('verifyCode').style.borderColor='#ef4444';
    setTimeout(()=>{ document.getElementById('verifyCode').style.borderColor=''; },1500);
    return;
  }
  btn.textContent = '확인 중...';
  btn.classList.add('disabled');
  btn.disabled = true;
  try {
    const res = await fetch(`${API}/verify-code`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email,code})
    });
    const data = await res.json();
    if(!res.ok) throw new Error(data.detail||'인증 실패');
    clearInterval(timerInterval);
    const remember = document.getElementById('rememberMe').checked;
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('ott_user', email);
    document.getElementById('successEmail').textContent = email+' 로 로그인되었습니다.';
    showStep(3);
    updateNavLogin(email);
  } catch(err) {
    alert('오류: '+err.message);
  } finally {
    btn.innerHTML = '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg> 확인';
    btn.classList.remove('disabled');
    btn.disabled = false;
  }
}

async function handleResend(){
  document.getElementById('verifyCode').value = '';
  clearInterval(timerInterval);
  showStep(1);
  await handleSendCode();
}

function startTimer(seconds){
  clearInterval(timerInterval);
  let s = seconds;
  const el = document.getElementById('timerCount');
  function tick(){
    const m=Math.floor(s/60), sec=s%60;
    if(el) el.textContent=`${m}:${sec.toString().padStart(2,'0')}`;
    if(s<=0){ clearInterval(timerInterval); if(el){el.textContent='만료됨';el.style.color='#ef4444';} }
    s--;
  }
  tick();
  timerInterval = setInterval(tick,1000);
}

function updateNavLogin(email){
  const btn=document.querySelector('.login-btn');
  if(btn){
    const name=email.split('@')[0];
    btn.textContent=name+' ▾';
    btn.onclick=()=>{
      if(confirm('로그아웃 하시겠습니까?')){
        localStorage.removeItem('ott_user');
        sessionStorage.removeItem('ott_user');
        btn.textContent='로그인';
        btn.onclick=openLogin;
      }
    };
  }
}

(function checkSavedLogin(){
  const email=localStorage.getItem('ott_user')||sessionStorage.getItem('ott_user');
  if(email) updateNavLogin(email);
})();

function handleGoogle(){ alert('Google 로그인은 준비 중입니다.'); }

document.addEventListener('keydown',function(e){ if(e.key==='Escape') closeLogin(); });
</script>
</body>
</html>
