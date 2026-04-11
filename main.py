<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SailorPiece — Login</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --black: #000000;
      --white: #ffffff;
      --gray-100: #f5f5f7;
      --gray-200: #e8e8ed;
      --gray-400: #6e6e73;
      --gray-600: #3a3a3c;
      --gray-800: #1c1c1e;
      --discord: #5865f2;
      --discord-hover: #4752c4;
    }

    html, body {
      height: 100%;
      background: var(--black);
      color: var(--white);
      font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
      -webkit-font-smoothing: antialiased;
      overflow: hidden;
    }

    /* ── Background grain + grid ── */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
      background-size: 60px 60px;
      pointer-events: none;
      z-index: 0;
    }

    body::after {
      content: '';
      position: fixed;
      inset: 0;
      background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(255,255,255,.06) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }

    /* ── Grain overlay ── */
    .grain {
      position: fixed;
      inset: 0;
      opacity: .3;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='.15'/%3E%3C/svg%3E");
      background-size: 200px;
      pointer-events: none;
      z-index: 0;
    }

    /* ── Glow blobs ── */
    .blob {
      position: fixed;
      border-radius: 50%;
      filter: blur(120px);
      pointer-events: none;
      z-index: 0;
      animation: drift 12s ease-in-out infinite alternate;
    }
    .blob-1 {
      width: 500px; height: 500px;
      background: rgba(255,255,255,.04);
      top: -150px; left: -100px;
      animation-delay: 0s;
    }
    .blob-2 {
      width: 400px; height: 400px;
      background: rgba(88,101,242,.06);
      bottom: -100px; right: -80px;
      animation-delay: -6s;
    }
    @keyframes drift {
      from { transform: translate(0, 0) scale(1); }
      to   { transform: translate(40px, 30px) scale(1.08); }
    }

    /* ── Layout ── */
    .page {
      position: relative;
      z-index: 1;
      height: 100vh;
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    /* ── Left panel ── */
    .left {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 52px 64px;
      border-right: 1px solid rgba(255,255,255,.07);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      width: 36px; height: 36px;
      border: 1.5px solid rgba(255,255,255,.3);
      border-radius: 10px;
      display: grid;
      place-items: center;
    }

    .brand-icon svg { width: 20px; height: 20px; }

    .brand-name {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -.3px;
      color: var(--white);
    }

    .hero-text {
      padding-bottom: 20px;
    }

    .hero-eyebrow {
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: rgba(255,255,255,.35);
      margin-bottom: 20px;
    }

    .hero-title {
      font-family: 'Noto Sans KR', sans-serif;
      font-size: clamp(36px, 3.5vw, 52px);
      font-weight: 300;
      line-height: 1.15;
      letter-spacing: -1.5px;
      color: var(--white);
      margin-bottom: 20px;
    }

    .hero-title strong {
      font-weight: 600;
    }

    .hero-desc {
      font-size: 15px;
      font-weight: 300;
      line-height: 1.7;
      color: rgba(255,255,255,.45);
      max-width: 380px;
    }

    .features {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .feature {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      color: rgba(255,255,255,.4);
    }

    .feature-dot {
      width: 5px; height: 5px;
      border-radius: 50%;
      background: rgba(255,255,255,.25);
      flex-shrink: 0;
    }

    /* ── Right panel ── */
    .right {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 52px 64px;
    }

    .card {
      width: 100%;
      max-width: 400px;
      animation: slideUp .6s cubic-bezier(.16,1,.3,1) both;
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(24px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .card-header {
      margin-bottom: 40px;
    }

    .card-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 20px;
      font-size: 11px;
      letter-spacing: .5px;
      color: rgba(255,255,255,.4);
      margin-bottom: 20px;
    }

    .card-tag span {
      width: 5px; height: 5px;
      border-radius: 50%;
      background: #5865f2;
      display: block;
    }

    .card-title {
      font-size: 26px;
      font-weight: 600;
      letter-spacing: -.8px;
      margin-bottom: 8px;
    }

    .card-sub {
      font-size: 14px;
      color: rgba(255,255,255,.35);
      font-weight: 300;
    }

    /* ── Divider ── */
    .divider {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 28px 0;
    }

    .divider-line {
      flex: 1;
      height: 1px;
      background: rgba(255,255,255,.08);
    }

    .divider-text {
      font-size: 11px;
      color: rgba(255,255,255,.2);
      letter-spacing: 1px;
    }

    /* ── Discord button ── */
    .btn-discord {
      width: 100%;
      padding: 16px 24px;
      background: #5865f2;
      border: none;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      font-size: 15px;
      font-weight: 500;
      color: #fff;
      cursor: pointer;
      transition: all .2s cubic-bezier(.16,1,.3,1);
      letter-spacing: -.2px;
      position: relative;
      overflow: hidden;
      font-family: inherit;
    }

    .btn-discord::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, rgba(255,255,255,.15) 0%, transparent 60%);
    }

    .btn-discord:hover {
      background: #4752c4;
      transform: translateY(-1px);
      box-shadow: 0 8px 30px rgba(88,101,242,.35);
    }

    .btn-discord:active {
      transform: translateY(0);
      box-shadow: none;
    }

    .discord-icon {
      width: 20px; height: 20px;
      flex-shrink: 0;
    }

    /* ── OR section ── */
    .manual-section {
      margin-top: 28px;
    }

    .input-group {
      margin-bottom: 14px;
    }

    .input-label {
      display: block;
      font-size: 12px;
      font-weight: 500;
      color: rgba(255,255,255,.4);
      margin-bottom: 8px;
      letter-spacing: .3px;
    }

    .input-field {
      width: 100%;
      padding: 13px 16px;
      background: rgba(255,255,255,.04);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 10px;
      font-size: 14px;
      color: var(--white);
      outline: none;
      transition: border-color .2s, background .2s;
      font-family: inherit;
    }

    .input-field::placeholder {
      color: rgba(255,255,255,.2);
    }

    .input-field:focus {
      border-color: rgba(255,255,255,.2);
      background: rgba(255,255,255,.06);
    }

    .btn-submit {
      width: 100%;
      padding: 14px 24px;
      background: var(--white);
      border: none;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      color: var(--black);
      cursor: pointer;
      transition: all .2s;
      letter-spacing: -.2px;
      margin-top: 6px;
      font-family: inherit;
    }

    .btn-submit:hover {
      background: var(--gray-100);
      transform: translateY(-1px);
    }

    /* ── Footer text ── */
    .card-footer {
      margin-top: 28px;
      text-align: center;
      font-size: 12px;
      color: rgba(255,255,255,.2);
      line-height: 1.6;
    }

    .card-footer a {
      color: rgba(255,255,255,.45);
      text-decoration: none;
      border-bottom: 1px solid rgba(255,255,255,.15);
      padding-bottom: 1px;
      transition: color .2s, border-color .2s;
    }

    .card-footer a:hover {
      color: rgba(255,255,255,.7);
      border-color: rgba(255,255,255,.4);
    }

    /* ── Status badge (top right) ── */
    .status-badge {
      position: fixed;
      top: 24px;
      right: 28px;
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 14px;
      background: rgba(255,255,255,.04);
      border: 1px solid rgba(255,255,255,.07);
      border-radius: 20px;
      font-size: 11px;
      color: rgba(255,255,255,.35);
      z-index: 10;
    }

    .status-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #30d158;
      box-shadow: 0 0 6px #30d158;
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: .5; }
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
      .page { grid-template-columns: 1fr; }
      .left { display: none; }
      .right { padding: 40px 28px; }
    }
  </style>
</head>
<body>
  <div class="grain"></div>
  <div class="blob blob-1"></div>
  <div class="blob blob-2"></div>

  <div class="status-badge">
    <div class="status-dot"></div>
    서버 정상
  </div>

  <div class="page">
    <!-- Left -->
    <div class="left">
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span class="brand-name">SailorPiece</span>
      </div>

      <div class="hero-text">
        <div class="hero-eyebrow">Roblox Auto Market</div>
        <h1 class="hero-title">
          로블록스<br>
          <strong>세일러 피스</strong><br>
          자동 거래 플랫폼
        </h1>
        <p class="hero-desc">
          디스코드 계정으로 간편하게 로그인하고 로블록스 세일러 피스 아이템을 자동으로 구매·판매하세요.
        </p>
      </div>

      <div class="features">
        <div class="feature">
          <div class="feature-dot"></div>
          디스코드 OAuth2 보안 인증
        </div>
        <div class="feature">
          <div class="feature-dot"></div>
          실시간 재고 자동 업데이트
        </div>
        <div class="feature">
          <div class="feature-dot"></div>
          구매 완료 시 디스코드 DM 알림
        </div>
        <div class="feature">
          <div class="feature-dot"></div>
          안전한 에스크로 결제 시스템
        </div>
      </div>
    </div>

    <!-- Right -->
    <div class="right">
      <div class="card">
        <div class="card-header">
          <div class="card-tag">
            <span></span>
            Discord OAuth2
          </div>
          <h2 class="card-title">로그인</h2>
          <p class="card-sub">디스코드 계정으로 안전하게 시작하세요</p>
        </div>

        <!-- Discord 로그인 -->
        <button class="btn-discord" onclick="handleDiscordLogin()">
          <svg class="discord-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.1 18.081.11 18.105.12 18.12a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
          </svg>
          Discord로 계속하기
        </button>

        <div class="divider">
          <div class="divider-line"></div>
          <div class="divider-text">또는</div>
          <div class="divider-line"></div>
        </div>

        <!-- 이메일 로그인 (보조) -->
        <div class="manual-section">
          <div class="input-group">
            <label class="input-label">이메일</label>
            <input class="input-field" type="email" placeholder="name@example.com" />
          </div>
          <div class="input-group">
            <label class="input-label">비밀번호</label>
            <input class="input-field" type="password" placeholder="••••••••" />
          </div>
          <button class="btn-submit">로그인</button>
        </div>

        <div class="card-footer">
          계정이 없으신가요? <a href="#">Discord로 가입</a><br><br>
          로그인 시 <a href="#">이용약관</a> 및 <a href="#">개인정보처리방침</a>에 동의합니다.
        </div>
      </div>
    </div>
  </div>

  <script>
    // Discord OAuth2 redirect
    // 실제 운영 시: CLIENT_ID, REDIRECT_URI를 교체하세요
    const DISCORD_CLIENT_ID = 'YOUR_CLIENT_ID';
    const REDIRECT_URI = encodeURIComponent(window.location.origin + '/auth/callback');
    const SCOPE = encodeURIComponent('identify email guilds');

    function handleDiscordLogin() {
      const url = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPE}`;
      
      // 데모 모드: 실제 배포 시 아래를 window.location.href = url; 로 교체
      showToast('Discord OAuth2 인증으로 이동 중...');
      setTimeout(() => {
        console.log('OAuth URL:', url);
      }, 500);
    }

    function showToast(msg) {
      const toast = document.createElement('div');
      toast.textContent = msg;
      Object.assign(toast.style, {
        position: 'fixed',
        bottom: '32px',
        left: '50%',
        transform: 'translateX(-50%) translateY(10px)',
        background: 'rgba(255,255,255,.95)',
        color: '#000',
        padding: '12px 20px',
        borderRadius: '10px',
        fontSize: '13px',
        fontWeight: '500',
        zIndex: '999',
        opacity: '0',
        transition: 'all .3s cubic-bezier(.16,1,.3,1)',
        whiteSpace: 'nowrap',
        boxShadow: '0 4px 24px rgba(0,0,0,.4)'
      });
      document.body.appendChild(toast);
      requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
      });
      setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
      }, 2500);
    }
  </script>
</body>
</html>
