BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    /* 전체 배경: 모바일/PC 모두 중앙 정렬 최적화 */
    body {{ background-color: #000; color: #fff; font-family: 'Inter', -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; overflow-x: hidden; }}
    
    /* 메인 박스: 28px의 둥근 모서리와 자동 크기 조절 */
    .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 45px 35px; border-radius: 28px; text-align: center; width: 100%; max-width: 380px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
    
    /* 로고 박스 */
    .logo-box {{ width: 75px; height: 75px; border-radius: 22px; background: #111; border: 1px solid #222; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 700; color: #fff; flex-shrink: 0; }}
    
    /* 제목 및 부제목: 텍스트 배열 똑바로 */
    h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -1px; text-align: center; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin-bottom: 35px; line-height: 1.6; text-align: center; width: 100%; max-width: 300px; }}
    
    /* 흰색 라운드 버튼 */
    .btn-main {{ background: #fff; color: #000; border: none; width: 100%; padding: 16px; border-radius: 16px; font-size: 15px; font-weight: 700; cursor: pointer; transition: 0.2s; text-decoration: none; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }}
    .btn-main:hover {{ background: #e5e5e5; transform: translateY(-2px); }}
    
    /* 상태 표시 박스: 배열 똑바로 */
    .status-alert {{ background: #111; border: 1px solid #222; border-left: 4px solid #fff; padding: 20px; text-align: left; font-size: 13px; color: #ccc; margin-bottom: 25px; border-radius: 14px; line-height: 1.5; width: 100%; box-sizing: border-box; }}
    
    .user-pill {{ background: #111; border: 1px solid #222; border-radius: 50px; padding: 10px 18px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; font-size: 13px; color: #888; width: 100%; box-sizing: border-box; gap: 10px; }}
    
    /* 클라우드플레어 Turnstile 위젯 중앙 정렬 */
    .cf-turnstile {{ margin-bottom: 25px; width: 100%; display: flex; justify-content: center; }}
    
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; text-align: center; }}
    
    /* 애니메이션 효과 */
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .fade {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
    
    /* 모바일용 추가 배열 최적화 */
    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; border-radius: 24px; }}
        h1 {{ font-size: 22px; }}
        .subtitle {{ font-size: 13px; }}
        .logo-box {{ width: 65px; height: 65px; font-size: 28px; }}
    }}
</style>
"""
