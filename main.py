<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SailorMarket — 로그인</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --discord:   #5865F2;
      --discord-h: #4752c4;
      --trans:     0.2s cubic-bezier(0.4,0,0.2,1);
    }

    html, body { height: 100%; }

    body {
      font-family: 'Noto Sans KR', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px 16px;
      background: #000;
      overflow-x: hidden;
    }

    /* ── 완전 흰색 카드 ── */
    .card {
      position: relative;
      width: 100%;
      max-width: 440px;
      background: #ffffff;
      border-radius: 24px;
      box-shadow:
        0 32px 80px rgba(0,0,0,0.5),
        0 8px 32px rgba(0,0,0,0.3);
      padding: 44px 40px 40px;
      animation: cardIn 0.55s cubic-bezier(0.22,1,0.36,1) both;
    }
    @keyframes cardIn {
      from { opacity: 0; transform: translateY(28px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* ── Badge ── */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: #eef0fe;
      border: 1px solid #c7cbfb;
      border-radius: 100px;
      padding: 5px 14px 5px 10px;
      font-size: 12px;
      font-weight: 500;
      color: #4752c4;
      margin-bottom: 20px;
      letter-spacing: 0.2px;
      animation: fadeUp 0.5s 0.1s both;
    }
    .badge-dot {
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--discord);
      box-shadow: 0 0 8px rgba(88,101,242,0.8);
      animation: dotPulse 2s ease-in-out infinite;
    }
    @keyframes dotPulse {
      0%,100% { box-shadow: 0 0 5px rgba(88,101,242,0.6); }
      50%      { box-shadow: 0 0 12px rgba(88,101,242,1); }
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Heading ── */
    .heading {
      margin-bottom: 26px;
      animation: fadeUp 0.5s 0.15s both;
    }
    .heading h1 {
      font-size: 30px;
      font-weight: 700;
      color: #111;
      letter-spacing: -0.6px;
      line-height: 1.15;
    }
    .heading p {
      font-size: 14px;
      color: #666;
      margin-top: 7px;
      line-height: 1.55;
    }

    /* ── Discord Btn ── */
    .btn-discord {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      height: 52px;
      background: var(--discord);
      border: none;
      border-radius: 13px;
      color: #fff;
      font-size: 15.5px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      text-decoration: none;
      transition: all var(--trans);
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(88,101,242,0.35);
      animation: fadeUp 0.5s 0.2s both;
      -webkit-tap-highlight-color: transparent;
    }
    .btn-discord::before {
      content: '';
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, transparent 60%);
    }
    .btn-discord:hover {
      background: var(--discord-h);
      transform: translateY(-1px);
      box-shadow: 0 8px 28px rgba(88,101,242,0.45);
    }
    .btn-discord:active { transform: scale(0.988); box-shadow: none; }

    /* ── Divider ── */
    .divider {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 22px 0;
      animation: fadeUp 0.5s 0.28s both;
    }
    .divider-line { flex: 1; height: 1px; background: #e5e7eb; }
    .divider-text { font-size: 12px; color: #aaa; letter-spacing: 0.3px; }

    /* ── Form ── */
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 14px;
      animation: fadeUp 0.5s 0.33s both;
    }
    .field label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #555;
      margin-bottom: 6px;
      letter-spacing: 0.15px;
    }
    .field-wrap { position: relative; }
    .field input {
      width: 100%;
      height: 48px;
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 11px;
      padding: 0 44px 0 14px;
      font-size: 15px;
      font-family: inherit;
      color: #111;
      outline: none;
      transition: all var(--trans);
      -webkit-appearance: none;
    }
    .field input::placeholder { color: #bbb; font-size: 14px; }
    .field input:focus {
      border-color: var(--discord);
      background: #fff;
      box-shadow: 0 0 0 3px rgba(88,101,242,0.1);
    }

    .pw-toggle {
      position: absolute;
      right: 12px; top: 50%;
      transform: translateY(-50%);
      background: none; border: none;
      cursor: pointer; padding: 4px;
      color: #bbb; display: flex;
      transition: color var(--trans);
    }
    .pw-toggle:hover { color: #777; }
    .pw-toggle .eye-off { display: none; }
    .pw-toggle.show .eye-on  { display: none; }
    .pw-toggle.show .eye-off { display: block; }

    .forgot { text-align: right; margin-top: -4px; }
    .forgot a {
      font-size: 12.5px;
      color: var(--discord);
      text-decoration: none;
      font-weight: 500;
      transition: opacity var(--trans);
    }
    .forgot a:hover { opacity: 0.7; }

    /* ── Login Btn ── */
    .btn-login {
      width: 100%;
      height: 50px;
      background: #111;
      border: none;
      border-radius: 13px;
      color: #fff;
      font-size: 15.5px;
      font-weight: 700;
      font-family: inherit;
      cursor: pointer;
      margin-top: 2px;
      transition: all var(--trans);
      position: relative;
      overflow: hidden;
      -webkit-tap-highlight-color: transparent;
    }
    .btn-login:hover {
      background: #222;
      box-shadow: 0 6px 24px rgba(0,0,0,0.2);
      transform: translateY(-1px);
    }
    .btn-login:active { transform: scale(0.988); }
    .btn-login .spinner {
      display: none;
      width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,0.25);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%,-50%);
    }
    @keyframes spin { to { transform: translate(-50%,-50%) rotate(360deg); } }
    .btn-login.loading .btn-text { opacity: 0; }
    .btn-login.loading .spinner  { display: block; }

    /* ── Footer ── */
    .footer-links {
      margin-top: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 7px;
      animation: fadeUp 0.5s 0.42s both;
    }
    .footer-links p { font-size: 13px; color: #888; text-align: center; }
    .footer-links a {
      color: var(--discord);
      text-decoration: none;
      font-weight: 600;
      transition: opacity var(--trans);
    }
    .footer-links a:hover { opacity: 0.7; }

    .terms {
      margin-top: 20px;
      text-align: center;
      font-size: 11.5px;
      color: #bbb;
      line-height: 1.7;
      animation: fadeUp 0.5s 0.48s both;
      padding-top: 18px;
      border-top: 1px solid #f0f0f0;
    }
    .terms a { color: #999; text-decoration: none; }
    .terms a:hover { color: #333; }

    /* ── Toast ── */
    .toast {
      position: fixed;
      top: 20px; left: 50%;
      transform: translateX(-50%) translateY(-80px);
      background: rgba(17,17,17,0.95);
      color: #fff;
      font-size: 13.5px;
      font-weight: 500;
      padding: 11px 22px;
      border-radius: 100px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
      z-index: 9999;
      transition: transform 0.4s cubic-bezier(0.34,1.56,0.64,1);
      white-space: nowrap;
      font-family: 'Noto Sans KR', sans-serif;
      pointer-events: none;
    }
    .toast.show { transform: translateX(-50%) translateY(0); }

    /* ── 반응형 ── */
    @media (max-width: 500px) {
      body { padding: 24px 14px; }
      .card { padding: 34px 22px 32px; border-radius: 20px; }
      .heading h1 { font-size: 26px; }
      .btn-discord, .btn-login { height: 52px; font-size: 15px; }
    }
  </style>
</head>
<body>

  <div class="toast" id="toast"></div>

  <div class="card">

    <div class="badge">
      <div class="badge-dot"></div>
      Discord OAuth2
    </div>

    <div class="heading">
      <h1>로그인</h1>
      <p>디스코드 계정으로 안전하게 시작하세요</p>
    </div>

    <a class="btn-discord" href="#" id="discordBtn" role="button">
      <svg width="22" height="16" viewBox="0 0 22 16" fill="none">
        <path d="M18.68 1.34A18.3 18.3 0 0 0 14.3 0c-.19.34-.4.8-.55 1.16a16.97 16.97 0 0 0-5.5 0A12.6 12.6 0 0 0 7.7 0 18.33 18.33 0 0 0 3.3 1.34 19.38 19.38 0 0 0 0 13.08a18.44 18.44 0 0 0 5.63 2.85c.46-.62.87-1.28 1.22-1.98a11.97 11.97 0 0 1-1.92-.92c.16-.12.32-.24.47-.37a13.1 13.1 0 0 0 11.2 0c.15.13.31.25.47.37-.61.36-1.26.67-1.93.92.35.7.76 1.36 1.22 1.98A18.4 18.4 0 0 0 22 13.08 19.35 19.38 0 0 0 18.68 1.34ZM7.34 10.7c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.95 2.41-2.15 2.41Zm7.32 0c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.94 2.41-2.15 2.41Z" fill="white"/>
      </svg>
      Discord로 계속하기
    </a>

    <div class="divider">
      <div class="divider-line"></div>
      <span class="divider-text">또는</span>
      <div class="divider-line"></div>
    </div>

    <div class="form-group">
      <div class="field">
        <label for="email">이메일</label>
        <div class="field-wrap">
          <input type="email" id="email" placeholder="name@example.com" autocomplete="email"/>
        </div>
      </div>

      <div class="field">
        <label for="password">비밀번호</label>
        <div class="field-wrap">
          <input type="password" id="password" placeholder="••••••••" autocomplete="current-password"/>
          <button class="pw-toggle" id="pwToggle" type="button" aria-label="비밀번호 보기">
            <svg class="eye-on" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12S5 4 12 4s11 8 11 8-4 8-11 8S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/>
            </svg>
            <svg class="eye-off" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
              <path d="m1 1 22 22"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="forgot">
        <a href="#" onclick="showToast('비밀번호 재설정 이메일을 발송했습니다.');return false;">비밀번호를 잊으셨나요?</a>
      </div>

      <button class="btn-login" id="loginBtn" type="button">
        <span class="btn-text">로그인</span>
        <div class="spinner"></div>
      </button>
    </div>

    <div class="footer-links">
      <p>계정이 없으신가요? <a href="#" onclick="showToast('Discord 가입 페이지로 이동합니다.');return false;">Discord로 가입</a></p>
      <p>회원가입: <a href="#" onclick="showToast('새 계정 만들기 페이지로 이동합니다.');return false;">새 계정 만들기</a></p>
    </div>

    <p class="terms">
      로그인 시 <a href="#">이용약관</a> 및 <a href="#">개인정보처리방침</a>에 동의합니다.
    </p>
  </div>

  <script>
    const CONFIG = {
      DISCORD_CLIENT_ID: 'YOUR_DISCORD_CLIENT_ID',
      REDIRECT_URI: window.location.origin + '/auth/callback',
    };

    function showToast(msg, ms = 2800) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), ms);
    }

    const pwToggle = document.getElementById('pwToggle');
    const pwInput  = document.getElementById('password');
    pwToggle.addEventListener('click', () => {
      const show = pwInput.type === 'password';
      pwInput.type = show ? 'text' : 'password';
      pwToggle.classList.toggle('show', show);
    });

    document.getElementById('discordBtn').addEventListener('click', (e) => {
      e.preventDefault();
      if (CONFIG.DISCORD_CLIENT_ID.startsWith('YOUR_')) {
        showToast('⚠️ Discord Client ID를 설정하세요.');
        return;
      }
      const params = new URLSearchParams({
        client_id:     CONFIG.DISCORD_CLIENT_ID,
        redirect_uri:  CONFIG.REDIRECT_URI,
        response_type: 'code',
        scope:         'identify email',
        state:         crypto.randomUUID(),
      });
      window.location.href = `https://discord.com/oauth2/authorize?${params}`;
    });

    document.getElementById('loginBtn').addEventListener('click', async () => {
      const email = document.getElementById('email').value.trim();
      const pw    = document.getElementById('password').value;
      if (!email || !pw) { showToast('이메일과 비밀번호를 입력하세요.'); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { showToast('올바른 이메일 형식이 아닙니다.'); return; }

      const btn = document.getElementById('loginBtn');
      btn.classList.add('loading'); btn.disabled = true;

      try {
        const res  = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password: pw }),
          credentials: 'include',
        });
        const data = await res.json();
        if (res.ok) {
          showToast('✅ 로그인 성공!');
          setTimeout(() => {
            window.location.href = data.is_admin ? '/admin/dashboard' : '/dashboard';
          }, 800);
        } else {
          showToast(data.message || '이메일 또는 비밀번호가 올바르지 않습니다.');
        }
      } catch {
        showToast('서버에 연결할 수 없습니다.');
      } finally {
        btn.classList.remove('loading'); btn.disabled = false;
      }
    });

    (function() {
      const p = new URLSearchParams(window.location.search);
      if (p.get('error')) showToast('로그인이 취소되었습니다.');
      if (p.get('code'))  showToast('✅ 인증 완료. 처리 중...');
    })();
  </script>
</body>
</html>
