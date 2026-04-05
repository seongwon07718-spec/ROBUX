import requests
import imaplib
import email
import re
import time

def get_2fa_code_from_gmail(gmail_user: str, gmail_password: str) -> str:
    """Gmail에서 Roblox 2FA 코드 자동 추출"""
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(gmail_user, gmail_password)
    mail.select("inbox")
    
    # 최근 Roblox 메일 검색
    time.sleep(5)  # 메일 도착 대기
    _, data = mail.search(None, 'FROM "noreply@roblox.com" UNSEEN')
    
    for num in data[0].split()[-1:]:
        _, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()
        
        # 6자리 코드 추출
        code = re.search(r'\b(\d{6})\b', body)
        if code:
            return code.group(1)
    return None

def login_roblox_with_2fa(username: str, password: str, gmail_user: str, gmail_password: str) -> str:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    
    # CSRF
    csrf = session.post("https://auth.roblox.com/v2/logout").headers.get("x-csrf-token")
    
    # 로그인
    resp = session.post(
        "https://auth.roblox.com/v2/login",
        json={"ctype": "Username", "cvalue": username, "password": password},
        headers={"x-csrf-token": csrf}
    )
    print(f"로그인: {resp.status_code} {resp.text}")
    
    # 2FA 필요한 경우
    if resp.status_code == 200 and "twoStepVerificationData" in resp.text:
        data = resp.json()
        ticket = data["twoStepVerificationData"]["ticket"]
        
        print("2FA 코드 이메일 대기중...")
        code = get_2fa_code_from_gmail(gmail_user, gmail_password)
        print(f"코드: {code}")
        
        # 2FA 제출
        verify_resp = session.post(
            "https://twostepverification.roblox.com/v1/users/verify",
            json={
                "username": username,
                "ticket": ticket,
                "code": code,
                "rememberDevice": True,
                "actionType": "Login"
            },
            headers={"x-csrf-token": csrf}
        )
        print(f"2FA 결과: {verify_resp.status_code} {verify_resp.text}")
    
    cookie = session.cookies.get(".ROBLOSECURITY")
    print(f"발급된 쿠키: {cookie[:30]}...")
    return cookie, session

if __name__ == "__main__":
    cookie, session = login_roblox_with_2fa(
        username="로블록스_아이디",
        password="로블록스_비밀번호",
        gmail_user="이메일@gmail.com",
        gmail_password="gmail_앱_비밀번호"  # Gmail 앱 비밀번호
    )
