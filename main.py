<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>로블록스 세일러 피스 자동 회 판매</title>
  <style>
    /* 기본 초기화 */
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
      background-color: #fff;
      color: #000;
      line-height: 1.6;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    a {
      color: inherit;
      text-decoration: none;
    }

    header {
      background: #fff;
      border-bottom: 1px solid #ddd;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 10;
    }

    header .logo {
      font-weight: 700;
      font-size: 1.4rem;
      letter-spacing: -0.02em;
    }

    nav {
      display: flex;
      gap: 24px;
    }

    nav a {
      font-weight: 500;
      font-size: 1rem;
      padding: 8px 0;
      transition: color 0.3s ease;
    }

    nav a:hover {
      color: #007aff; /* 애플 블루 하이라이트 */
    }

    /* 모바일 햄버거 메뉴 */
    .menu-toggle {
      display: none;
      flex-direction: column;
      gap: 5px;
      cursor: pointer;
    }

    .menu-toggle span {
      width: 25px;
      height: 3px;
      background: #000;
      border-radius: 2px;
    }

    main {
      flex-grow: 1;
      max-width: 1200px;
      margin: 32px auto;
      padding: 0 24px;
    }

    .hero {
      text-align: center;
      margin-bottom: 48px;
    }

    .hero h1 {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 12px;
    }

    .hero p {
      font-size: 1.2rem;
      color: #333;
    }

    .features {
      display: flex;
      gap: 24px;
      justify-content: center;
      flex-wrap: wrap;
    }

    .feature-card {
      background: #f9f9f9;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      padding: 24px;
      flex-basis: 280px;
      text-align: center;
      color: #111;
    }

    .feature-card h3 {
      margin-bottom: 12px;
      font-weight: 600;
    }

    button.primary-btn {
      margin-top: 24px;
      background-color: #000;
      color: #fff;
      border: none;
      padding: 12px 28px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      font-size: 1rem;
      transition: background-color 0.3s ease;
    }

    button.primary-btn:hover {
      background-color: #333;
    }

    footer {
      background: #000;
      color: #fff;
      padding: 20px 24px;
      text-align: center;
      font-size: 0.9rem;
    }

    /* 반응형 */

    @media (max-width: 768px) {
      nav {
        display: none;
        flex-direction: column;
        gap: 16px;
        background: #fff;
        position: absolute;
        top: 64px;
        right: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-radius: 12px;
        padding: 16px 24px;
      }

      nav.active {
        display: flex;
      }

      .menu-toggle {
        display: flex;
      }

      .features {
        flex-direction: column;
        gap: 16px;
      }

      main {
        padding: 0 16px;
        margin: 24px auto;
      }
    }
  </style>
</head>
<body>

<header>
  <div class="logo">SailorPiece</div>
  <nav id="nav-menu">
    <a href="#">홈</a>
    <a href="#">자동 회 판매</a>
    <a href="#">내 계정</a>
    <a href="#">고객센터</a>
  </nav>
  <button class="menu-toggle" id="menu-toggle" aria-label="메뉴 토글">
    <span></span>
    <span></span>
    <span></span>
  </button>
</header>

<main>
  <section class="hero">
    <h1>로블록스 세일러 피스 자동 회 판매 플랫폼</h1>
    <p>간편하고 안전하게 자동 회를 구매하세요.</p>
    <button class="primary-btn">지금 시작하기</button>
  </section>

  <section class="features">
    <div class="feature-card">
      <h3>24시간 자동 판매</h3>
      <p>언제든지 원할 때 구매 가능, 빠르고 정확한 자동화 시스템</p>
    </div>
    <div class="feature-card">
      <h3>안전한 거래 보장</h3>
      <p>투명하고 안정적인 거래로 신뢰를 제공합니다.</p>
    </div>
    <div class="feature-card">
      <h3>PC & 모바일 호환</h3>
      <p>모든 기기에서 최적화된 UI/UX를 경험하세요.</p>
    </div>
  </section>
</main>

<footer>
  © 2026 SailorPiece. All Rights Reserved.
</footer>

<script>
  // 모바일 메뉴 토글
  const menuToggle = document.getElementById('menu-toggle');
  const navMenu = document.getElementById('nav-menu');
  menuToggle.addEventListener('click', () => {
    navMenu.classList.toggle('active');
  });
</script>

</body>
</html>
