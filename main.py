<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
  <title>SailorMarket — 로그인</title>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --discord:   #5865F2;
      --discord-h: #4752c4;
      --trans:     0.2s cubic-bezier(0.4,0,0.2,1);
    }

    /* 화면 고정 */
    html, body {
      width: 100%; height: 100%;
      overflow: hidden;
    }

    body {
      font-family: 'Noto Sans KR', -apple-system, sans-serif;
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      position: fixed;
      inset: 0;
    }

    /* ── 탭 전환 래퍼 ── */
    .wrapper {
      width: 100%;
      max-width: 440px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    /* ── 흰색 카드 ── */
    .card {
      width: 100%;
      background: #fff;
      border-radius: 24px;
      box-shadow: 0 32px 80px rgba(0,0,0,0.5), 0 8px 32px rgba(0,0,0,0.3);
      padding: 40px 36px 36px;
      animation: cardIn 0.5s cubic-bezier(0.22,1,0.36,1) both;
    }
    @keyframes cardIn {
      from { opacity: 0; transform: translateY(24px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* ── 탭 (로그인 / 회원가입) ── */
    .tabs {
      display: flex;
      background: #f3f4f6;
      border-radius: 12px;
      padding: 4px;
      margin-bottom: 28px;
      gap: 4px;
    }
    .tab-btn {
      flex: 1;
      height: 38px;
      border: none;
      border-radius: 9px;
      background: transparent;
      font-family: inherit;
      font-size: 14px;
      font-weight: 600;
      color: #888;
      cursor: pointer;
      transition: all var(--trans);
    }
    .tab-btn.active {
      background: #fff;
      color: #111;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* ── Badge ── */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: #eef0fe;
      border: 1px solid #c7cbfb;
      border-radius: 100px;
      padding: 4px 12px 4px 9px;
      font-size: 11.5px;
      font-weight: 500;
      color: #4752c4;
      margin-bottom: 16px;
    }
    .badge-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--discord);
      animation: dotPulse 2s ease-in-out infinite;
    }
    @keyframes dotPulse {
      0%,100% { box-shadow: 0 0 4px rgba(88,101,242,0.6); }
      50%      { box-shadow: 0 0 10px rgba(88,101,242,1); }
    }

    /* ── Heading ── */
    .heading { margin-bottom: 22px; }
    .heading h1 {
      font-size: 26px;
      font-weight: 700;
      color: #111;
      letter-spacing: -0.5px;
    }
    .heading p {
      font-size: 13.5px;
      color: #666;
      margin-top: 5px;
      line-height: 1.5;
    }

    /* ── Discord Btn ── */
    .btn-discord {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      width: 100%;
      height: 50px;
      background: var(--discord);
      border: none;
      border-radius: 13px;
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      text-decoration: none;
      transition: all var(--trans);
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 18px rgba(88,101,242,0.35);
      -webkit-tap-highlight-color: transparent;
    }
    .btn-discord::before {
      content: '';
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, transparent 60%);
    }
    .btn-discord:hover { background: var(--discord-h); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(88,101,242,0.45); }
    .btn-discord:active { transform: scale(0.988); }

    /* ── Divider ── */
    .divider {
      display: flex; align-items: center; gap: 12px;
      margin: 18px 0;
    }
    .divider-line { flex: 1; height: 1px; background: #e5e7eb; }
    .divider-text { font-size: 11.5px; color: #bbb; }

    /* ── Form ── */
    .form-group { display: flex; flex-direction: column; gap: 12px; }

    .field label {
      display: block;
      font-size: 11.5px;
      font-weight: 600;
      color: #555;
      margin-bottom: 5px;
    }
    .field-wrap { position: relative; }
    .field input {
      width: 100%;
      height: 46px;
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 11px;
      padding: 0 42px 0 13px;
      font-size: 14.5px;
      font-family: inherit;
      color: #111;
      outline: none;
      transition: all var(--trans);
      -webkit-appearance: none;
    }
    .field input::placeholder { color: #bbb; font-size: 13.5px; }
    .field input:focus {
      border-color: var(--discord);
      background: #fff;
      box-shadow: 0 0 0 3px rgba(88,101,242,0.1);
    }
    .field input.error { border-color: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.1); }

    .pw-toggle {
      position: absolute; right: 11px; top: 50%;
      transform: translateY(-50%);
      background: none; border: none; cursor: pointer; padding: 4px;
      color: #bbb; display: flex; transition: color var(--trans);
    }
    .pw-toggle:hover { color: #777; }
    .pw-toggle .eye-off { display: none; }
    .pw-toggle.show .eye-on  { display: none; }
    .pw-toggle.show .eye-off { display: block; }

    .form-meta {
      display: flex; justify-content: flex-end; margin-top: -4px;
    }
    .form-meta a {
      font-size: 12px; color: var(--discord);
      text-decoration: none; font-weight: 500;
      transition: opacity var(--trans);
    }
    .form-meta a:hover { opacity: 0.7; }

    /* 에러 메시지 */
    .err-msg {
      font-size: 11.5px;
      color: #ef4444;
      margin-top: -6px;
      display: none;
    }
    .err-msg.show { display: block; }

    /* ── 주 버튼 ── */
    .btn-main {
      width: 100%;
      height: 48px;
      background: #111;
      border: none;
      border-radius: 13px;
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      font-family: inherit;
      cursor: pointer;
      margin-top: 4px;
      transition: all var(--trans);
      position: relative;
      overflow: hidden;
      -webkit-tap-highlight-color: transparent;
    }
    .btn-main:hover { background: #222; box-shadow: 0 6px 20px rgba(0,0,0,0.18); transform: translateY(-1px); }
    .btn-main:active { transform: scale(0.988); }
    .btn-main .spinner {
      display: none;
      width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,0.25);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%,-50%);
    }
    @keyframes spin { to { transform: translate(-50%,-50%) rotate(360deg); } }
    .btn-main.loading .btn-text { opacity: 0; }
    .btn-main.loading .spinner  { display: block; }

    /* ── Terms (회원가입 탭) ── */
    .signup-terms {
      font-size: 11px;
      color: #aaa;
      text-align: center;
      line-height: 1.6;
      margin-top: 10px;
    }
    .signup-terms a { color: #888; text-decoration: underline; }

    /* ── Toast ── */
    .toast {
      position: fixed;
      top: 20px; left: 50%;
      transform: translateX(-50%) translateY(-80px);
      background: rgba(17,17,17,0.95);
      color: #fff;
      font-size: 13px;
      font-weight: 500;
      padding: 10px 20px;
      border-radius: 100px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
      z-index: 9999;
      transition: transform 0.4s cubic-bezier(0.34,1.56,0.64,1);
      white-space: nowrap;
      pointer-events: none;
    }
    .toast.show { transform: translateX(-50%) translateY(0); }
    .toast.success { background: rgba(22,163,74,0.95); }
    .toast.error   { background: rgba(220,38,38,0.95); }

    /* ── 반응형 ── */
    @media (max-width: 480px) {
      .wrapper { padding: 12px; }
      .card { padding: 30px 20px 28px; border-radius: 20px; }
      .heading h1 { font-size: 22px; }
    }
    @media (max-height: 650px) {
      .card { padding: 24px 28px 24px; }
      .heading { margin-bottom: 16px; }
      .form-group { gap: 10px; }
      .divider { margin: 14px 0; }
    }
  </style>
</head>
<body>

  <div class="toast" id="toast"></div>

  <div class="wrapper">
    <div class="card">

      <!-- 탭 -->
      <div class="tabs">
        <button class="tab-btn active" id="tabLogin" onclick="switchTab('login')">로그인</button>
        <button class="tab-btn" id="tabSignup" onclick="switchTab('signup')">회원가입</button>
      </div>

      <!-- ══ 로그인 패널 ══ -->
      <div id="panelLogin">
        <div class="badge"><div class="badge-dot"></div>Discord OAuth2</div>
        <div class="heading">
          <h1>로그인</h1>
          <p>디스코드 계정으로 안전하게 시작하세요</p>
        </div>

        <button class="btn-discord" id="btnDiscordLogin">
          <svg width="20" height="15" viewBox="0 0 22 16" fill="none">
            <path d="M18.68 1.34A18.3 18.3 0 0 0 14.3 0c-.19.34-.4.8-.55 1.16a16.97 16.97 0 0 0-5.5 0A12.6 12.6 0 0 0 7.7 0 18.33 18.33 0 0 0 3.3 1.34 19.38 19.38 0 0 0 0 13.08a18.44 18.44 0 0 0 5.63 2.85c.46-.62.87-1.28 1.22-1.98a11.97 11.97 0 0 1-1.92-.92c.16-.12.32-.24.47-.37a13.1 13.1 0 0 0 11.2 0c.15.13.31.25.47.37-.61.36-1.26.67-1.93.92.35.7.76 1.36 1.22 1.98A18.4 18.4 0 0 0 22 13.08 19.35 19.38 0 0 0 18.68 1.34ZM7.34 10.7c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.95 2.41-2.15 2.41Zm7.32 0c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.94 2.41-2.15 2.41Z" fill="white"/>
          </svg>
          Discord로 로그인
        </button>

        <div class="divider">
          <div class="divider-line"></div>
          <span class="divider-text">또는 이메일로</span>
          <div class="divider-line"></div>
        </div>

        <div class="form-group">
          <div class="field">
            <label for="loginEmail">이메일</label>
            <div class="field-wrap">
              <input type="email" id="loginEmail" placeholder="name@example.com" autocomplete="email"/>
            </div>
          </div>
          <div class="field">
            <label for="loginPw">비밀번호</label>
            <div class="field-wrap">
              <input type="password" id="loginPw" placeholder="••••••••" autocomplete="current-password"/>
              <button class="pw-toggle" id="toggleLoginPw" type="button">
                <svg class="eye-on" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12S5 4 12 4s11 8 11 8-4 8-11 8S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg class="eye-off" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><path d="m1 1 22 22"/></svg>
              </button>
            </div>
          </div>
          <div class="form-meta">
            <a href="#" onclick="showToast('비밀번호 재설정 이메일을 발송했습니다.','success');return false;">비밀번호를 잊으셨나요?</a>
          </div>
          <p class="err-msg" id="loginErr"></p>
          <button class="btn-main" id="btnLogin">
            <span class="btn-text">로그인</span>
            <div class="spinner"></div>
          </button>
        </div>
      </div>

      <!-- ══ 회원가입 패널 ══ -->
      <div id="panelSignup" style="display:none;">
        <div class="badge"><div class="badge-dot"></div>Discord OAuth2</div>
        <div class="heading">
          <h1>회원가입</h1>
          <p>Discord로 바로 가입하거나 이메일로 시작하세요</p>
        </div>

        <button class="btn-discord" id="btnDiscordSignup">
          <svg width="20" height="15" viewBox="0 0 22 16" fill="none">
            <path d="M18.68 1.34A18.3 18.3 0 0 0 14.3 0c-.19.34-.4.8-.55 1.16a16.97 16.97 0 0 0-5.5 0A12.6 12.6 0 0 0 7.7 0 18.33 18.33 0 0 0 3.3 1.34 19.38 19.38 0 0 0 0 13.08a18.44 18.44 0 0 0 5.63 2.85c.46-.62.87-1.28 1.22-1.98a11.97 11.97 0 0 1-1.92-.92c.16-.12.32-.24.47-.37a13.1 13.1 0 0 0 11.2 0c.15.13.31.25.47.37-.61.36-1.26.67-1.93.92.35.7.76 1.36 1.22 1.98A18.4 18.4 0 0 0 22 13.08 19.35 19.38 0 0 0 18.68 1.34ZM7.34 10.7c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.95 2.41-2.15 2.41Zm7.32 0c-1.18 0-2.15-1.08-2.15-2.41 0-1.33.95-2.42 2.15-2.42s2.17 1.09 2.15 2.42c0 1.33-.94 2.41-2.15 2.41Z" fill="white"/>
          </svg>
          Discord로 회원가입
        </button>

        <div class="divider">
          <div class="divider-line"></div>
          <span class="divider-text">또는 이메일로</span>
          <div class="divider-line"></div>
        </div>

        <div class="form-group">
          <div class="field">
            <label for="signupEmail">이메일</label>
            <div class="field-wrap">
              <input type="email" id="signupEmail" placeholder="name@example.com" autocomplete="email"/>
            </div>
          </div>
          <div class="field">
            <label for="signupPw">비밀번호</label>
            <div class="field-wrap">
              <input type="password" id="signupPw" placeholder="8자 이상" autocomplete="new-password"/>
              <button class="pw-toggle" id="toggleSignupPw" type="button">
                <svg class="eye-on" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12S5 4 12 4s11 8 11 8-4 8-11 8S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg class="eye-off" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><path d="m1 1 22 22"/></svg>
              </button>
            </div>
          </div>
          <div class="field">
            <label for="signupPw2">비밀번호 확인</label>
            <div class="field-wrap">
              <input type="password" id="signupPw2" placeholder="비밀번호 재입력" autocomplete="new-password"/>
            </div>
          </div>
          <p class="err-msg" id="signupErr"></p>
          <button class="btn-main" id="btnSignup">
            <span class="btn-text">회원가입</span>
            <div class="spinner"></div>
          </button>
          <p class="signup-terms">가입 시 <a href="#">이용약관</a> 및 <a href="#">개인정보처리방침</a>에 동의합니다.</p>
        </div>
      </div>

    </div>
  </div>

  <script>
    // ── 설정: DISCORD_CLIENT_ID를 .env의 값으로 교체하세요 ──
    const DISCORD_CLIENT_ID = 'YOUR_DISCORD_CLIENT_ID';
    const REDIRECT_URI      = window.location.origin + '/auth/discord/callback';

    // ── 탭 전환 ──
    function switchTab(tab) {
      const isLogin = tab === 'login';
      document.getElementById('panelLogin').style.display  = isLogin ? '' : 'none';
      document.getElementById('panelSignup').style.display = isLogin ? 'none' : '';
      document.getElementById('tabLogin').classList.toggle('active', isLogin);
      document.getElementById('tabSignup').classList.toggle('active', !isLogin);
      clearErrors();
    }

    function clearErrors() {
      document.querySelectorAll('.err-msg').forEach(e => { e.textContent = ''; e.classList.remove('show'); });
      document.querySelectorAll('.field input').forEach(i => i.classList.remove('error'));
    }

    function showErr(id, msg) {
      const el = document.getElementById(id);
      el.textContent = msg; el.classList.add('show');
    }

    // ── Toast ──
    let toastTimer;
    function showToast(msg, type = '', ms = 2800) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.className = 'toast show' + (type ? ' ' + type : '');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => t.className = 'toast', ms);
    }

    // ── 비밀번호 토글 ──
    function makePwToggle(toggleId, inputId) {
      document.getElementById(toggleId).addEventListener('click', () => {
        const inp = document.getElementById(inputId);
        const show = inp.type === 'password';
        inp.type = show ? 'text' : 'password';
        document.getElementById(toggleId).classList.toggle('show', show);
      });
    }
    makePwToggle('toggleLoginPw',  'loginPw');
    makePwToggle('toggleSignupPw', 'signupPw');

    // ── Discord OAuth 공통 ──
    function discordOAuth(mode) {
      if (DISCORD_CLIENT_ID === 'YOUR_DISCORD_CLIENT_ID') {
        showToast('⚠️ DISCORD_CLIENT_ID를 설정하세요.', 'error'); return;
      }
      const state = mode + '_' + crypto.randomUUID(); // 모드 구분용 state
      sessionStorage.setItem('oauth_state', state);
      const params = new URLSearchParams({
        client_id:     DISCORD_CLIENT_ID,
        redirect_uri:  REDIRECT_URI,
        response_type: 'code',
        scope:         'identify email',
        state,
        prompt:        mode === 'signup' ? 'consent' : 'none',
      });
      window.location.href = `https://discord.com/oauth2/authorize?${params}`;
    }

    document.getElementById('btnDiscordLogin').addEventListener('click',  () => discordOAuth('login'));
    document.getElementById('btnDiscordSignup').addEventListener('click', () => discordOAuth('signup'));

    // ── 이메일 로그인 ──
    document.getElementById('btnLogin').addEventListener('click', async () => {
      clearErrors();
      const email = document.getElementById('loginEmail').value.trim();
      const pw    = document.getElementById('loginPw').value;
      if (!email) { document.getElementById('loginEmail').classList.add('error'); showErr('loginErr', '이메일을 입력하세요.'); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { document.getElementById('loginEmail').classList.add('error'); showErr('loginErr', '올바른 이메일 형식이 아닙니다.'); return; }
      if (!pw) { document.getElementById('loginPw').classList.add('error'); showErr('loginErr', '비밀번호를 입력하세요.'); return; }

      const btn = document.getElementById('btnLogin');
      btn.classList.add('loading'); btn.disabled = true;
      try {
        const res  = await fetch('/api/auth/login', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password: pw }),
        });
        const data = await res.json();
        if (res.ok) {
          showToast('✅ 로그인 성공!', 'success');
          setTimeout(() => { window.location.href = data.is_admin ? '/admin/dashboard' : '/dashboard'; }, 700);
        } else {
          showErr('loginErr', data.message || '이메일 또는 비밀번호가 올바르지 않습니다.');
        }
      } catch { showErr('loginErr', '서버에 연결할 수 없습니다.'); }
      finally { btn.classList.remove('loading'); btn.disabled = false; }
    });

    // ── 이메일 회원가입 ──
    document.getElementById('btnSignup').addEventListener('click', async () => {
      clearErrors();
      const email = document.getElementById('signupEmail').value.trim();
      const pw    = document.getElementById('signupPw').value;
      const pw2   = document.getElementById('signupPw2').value;
      if (!email) { document.getElementById('signupEmail').classList.add('error'); showErr('signupErr', '이메일을 입력하세요.'); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { document.getElementById('signupEmail').classList.add('error'); showErr('signupErr', '올바른 이메일 형식이 아닙니다.'); return; }
      if (pw.length < 8) { document.getElementById('signupPw').classList.add('error'); showErr('signupErr', '비밀번호는 8자 이상이어야 합니다.'); return; }
      if (pw !== pw2) { document.getElementById('signupPw2').classList.add('error'); showErr('signupErr', '비밀번호가 일치하지 않습니다.'); return; }

      const btn = document.getElementById('btnSignup');
      btn.classList.add('loading'); btn.disabled = true;
      try {
        const res  = await fetch('/api/auth/register', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password: pw }),
        });
        const data = await res.json();
        if (res.ok) {
          showToast('✅ 회원가입 완료! 로그인해주세요.', 'success');
          setTimeout(() => switchTab('login'), 1200);
        } else {
          showErr('signupErr', data.message || '회원가입에 실패했습니다.');
        }
      } catch { showErr('signupErr', '서버에 연결할 수 없습니다.'); }
      finally { btn.classList.remove('loading'); btn.disabled = false; }
    });

    // ── Enter 키 지원 ──
    document.getElementById('loginPw').addEventListener('keydown',   e => { if (e.key === 'Enter') document.getElementById('btnLogin').click(); });
    document.getElementById('signupPw2').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('btnSignup').click(); });

    // ── OAuth 콜백 처리 ──
    (function() {
      const p = new URLSearchParams(window.location.search);
      if (p.get('error'))         showToast('Discord 로그인이 취소되었습니다.', 'error');
      if (p.get('discord_error')) showToast(decodeURIComponent(p.get('discord_error')), 'error');
      if (p.get('discord_ok'))    { showToast('✅ Discord 로그인 성공!', 'success'); setTimeout(() => window.location.href = '/dashboard', 700); }
    })();
  </script>
</body>
</html>
