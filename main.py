# 1. BASE_STYLE (기존 스타일 유지 + 로딩 바 스타일 추가)
BASE_STYLE = f"""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
    
    body {{ background-color: #000; color: #fff; font-family: 'Inter', -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; overflow-x: hidden; }}
    .card {{ background: #0a0a0a; border: 1px solid #1a1a1a; padding: 45px 35px; border-radius: 28px; text-align: center; width: 100%; max-width: 380px; box-shadow: 0 25px 50px rgba(0,0,0,0.8); box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
    .logo-box {{ width: 75px; height: 75px; border-radius: 22px; background: #111; border: 1px solid #222; margin: 0 auto 30px; display: flex; justify-content: center; align-items: center; font-size: 32px; font-weight: 700; color: #fff; flex-shrink: 0; }}
    h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -1px; text-align: center; width: 100%; }}
    .subtitle {{ color: #666; font-size: 14px; margin-bottom: 35px; line-height: 1.6; text-align: center; width: 100%; max-width: 300px; }}
    .status-alert {{ background: #111; border: 1px solid #222; border-left: 4px solid #fff; padding: 20px; text-align: left; font-size: 13px; color: #ccc; margin-bottom: 25px; border-radius: 14px; line-height: 1.5; width: 100%; box-sizing: border-box; }}
    .footer {{ color: #333; font-size: 11px; margin-top: 35px; letter-spacing: 1px; width: 100%; text-align: center; }}
    .fade {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1); }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    /* 로딩 바 추가 스타일 */
    .progress-container {{ width: 100%; margin-bottom: 25px; }}
    .progress-bg {{ background: #1a1a1a; height: 8px; width: 100%; border-radius: 10px; overflow: hidden; margin-bottom: 10px; }}
    .progress-bar {{ background: #fff; height: 100%; width: 0%; transition: width 0.04s linear; }}
    .percent-text {{ font-size: 14px; color: #fff; font-weight: 700; }}

    @media (max-width: 480px) {{
        .card {{ padding: 35px 25px; border-radius: 24px; }}
        h1 {{ font-size: 22px; }}
        .subtitle {{ font-size: 13px; }}
        .logo-box {{ width: 65px; height: 65px; font-size: 28px; }}
    }}
</style>
"""

# 2. 결과 화면 HTML (로딩 4초 로직 적용)
@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    # ... (데이터베이스 저장 로직 생략) ...
    
    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
        <div class="card fade">
            <div id="loading-box" style="width:100%;">
                <div class="logo-box">🔒</div>
                <h1>보안 확인 중</h1>
                <p class="subtitle">계정 권한을 확인하고 있습니다.<br>잠시만 기다려 주세요.</p>
                <div class="progress-container">
                    <div class="progress-bg"><div id="bar" class="progress-bar"></div></div>
                    <div id="percent" class="percent-text">0%</div>
                </div>
            </div>

            <div id="success-box" style="display:none; width:100%;">
                <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                <h1>인증 완료</h1>
                <p class="subtitle">보안 검사가 성공적으로 끝났습니다.</p>
                <div class="status-alert" style="text-align:center;">성공적으로 승인되었습니다.</div>
                <div class="footer">SERVICE VOUT VERIFIED</div>
            </div>
        </div>

        <script>
            let val = 0;
            const bar = document.getElementById('bar');
            const txt = document.getElementById('percent');
            const load = document.getElementById('loading-box');
            const succ = document.getElementById('success-box');

            // 4초(4000ms) 동안 100% 채우기 (40ms마다 1%씩)
            const timer = setInterval(() => {{
                val++;
                bar.style.width = val + '%';
                txt.innerText = val + '%';

                if (val >= 100) {{
                    clearInterval(timer);
                    load.style.display = 'none';
                    succ.style.display = 'block';
                }}
            }}, 40); 
        </script>
    </body></html>
    """
