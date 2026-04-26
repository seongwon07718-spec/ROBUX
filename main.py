tunnel: ott-server
credentials-file: ~/.cloudflared/<터널ID>.json

ingress:
  - hostname: 도메인.com
    service: http://localhost:8000
  - service: http_status:404
