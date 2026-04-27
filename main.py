tunnel: vout
credentials-file: C:\Users\user\.cloudflared\[터널ID].json

ingress:
  - hostname: kakaobank.v0ut.com
    service: http://localhost:8000
  - service: http_status:404
