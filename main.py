tunnel: ac786224-2c27-4e81-b029-55dd0b047370
credentials-file: C:\Users\user\.cloudflared\ac786224-2c27-4e81-b029-55dd0b047370.json

ingress:
  - hostname: 여기에도메인.com
    service: http://localhost:8000
  - service: http_status:404
