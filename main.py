@app.post("/verify", response_class=HTMLResponse)
async def verify_turnstile(request: Request, server_id: str = Form(...), access_token: str = Form(...), user_id: str = Form(...)):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")

    async with aiohttp.ClientSession() as session:
        verify_data = {'secret': CF_TURNSTILE_SECRET_KEY, 'response': turnstile_response}
        async with session.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=verify_data) as resp:
            result = await resp.json()
            
            if result.get("success"):
                conn = sqlite3.connect('restore_user.db')
                conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, server_id, access_token))
                conn.commit()
                conn.close()
                
                return f"""
                <html><head>{BASE_STYLE}</head>
                <body>
                    <div class="card fade">
                        <div class="logo-box" style="background:#fff; color:#000;">✓</div>
                        <h1>인증 완료</h1>
                        <p class="subtitle">보안 검사가 성공적으로 끝났습니다</p>
                        <div class="status-alert" style="border-left-color:#fff; text-align:center;">성공적으로 승인되었습니다.</div>
                        <div class="footer">SERVICE VOUT VERIFIED</div>
                    </div>
                </body></html>
                """
            else:
                return "보안 검증 실패 다시 시도해 주세요"
