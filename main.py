BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    /* 1. 배경 및 전체 화면 중앙 정렬 */
    body {{ 
        background-color: #000; 
        color: #fff; 
        font-family: 'Inter', -apple-system, sans-serif; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        min-height: 100vh; 
        margin: 0; 
        padding: 0;
        box-sizing: border-box; 
    }}
    
    /* 2. 메인 카드 */
    .card {{ 
        background: #0a0a0a; 
        border: 1px solid #1a1a1a; 
        padding: 45px 30px; 
        border-radius: 28px; 
        text-align: center; 
        width: 90%; 
        max-width: 360px; 
        box-shadow: 0 25px 50px rgba(0,0,0,0.8); 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        box-sizing: border-box;
    }}
    
    /* 3. 로고 박스 정렬 */
    .logo-box {{ 
        width: 70px; 
        height: 70px; 
        border-radius: 20px; 
        background: #111; 
        border: 1px solid #222; 
        margin: 0 auto 25px auto; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        font-size: 32px; 
    }}
    
    h1 {{ font-size: 24px; font-weight: 700; margin: 0 0 10px 0; letter-spacing: -0.5px; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin: 0 0 30px 0; line-height: 1.5; width: 100%; word-break: keep-all; }}
    
    /* [수정] 캡차 위젯과 버튼 사이를 20px로 조정 (기존보다 절반 이상 줄임) */
    .cf-turnstile {{ 
        margin-bottom: 20px !important; 
        width: 100%; 
        display: flex; 
        justify-content: center; 
    }}
    
    /* 4. 상태 바 */
    .status-alert {{ 
        background: #111; 
        border: 1px solid #222; 
        border-left: 4px solid #fff; 
        padding: 18px 10px; 
        text-align: center; 
        font-size: 13px; 
        color: #ccc; 
        margin-bottom: 20px; 
        border-radius: 12px; 
        width: 100%; 
        box-sizing: border-box; 
        display: block;
    }}
    
    /* 5. 사용자 정보 및 로딩 바 */
    .user-pill {{ 
        background: #111; 
        border: 1px solid #222; 
        border-radius: 50px; 
        padding: 12px 20px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 25px; 
        font-size: 13px; 
        width: 100%; 
        box-sizing: border-box; 
    }}
    
    .progress-wrap {{ width: 100%; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; }}
    .progress-bg {{ background: #1a1a1a; height: 6px; width: 100%; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }}
    .progress-bar {{ background: #fff; height: 100%; width: 0%; transition: width 0.05s linear; }}
    
    .btn-main {{ 
        background: #fff; 
        color: #000; 
        border: none; 
        width: 100%; 
        padding: 18px; 
        border-radius: 16px; 
        font-size: 16px; 
        font-weight: 700; 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        cursor: pointer;
        text-decoration: none;
    }}
    
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; }}
    
    .fade {{ animation: fadeInUp 0.6s ease-out; }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(15px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; }}
        h1 {{ font-size: 22px; }}
    }}
</style>
"""
