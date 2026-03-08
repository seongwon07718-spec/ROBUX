import json
import os
import sys
import urllib.request
import urllib.error


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_port = os.getenv("CHARGE_API_PORT", "88")
_default_url = f"http://127.0.0.1:{_port}/"
CHARGE_API_URL = os.getenv("CHARGE_API_URL", _default_url).strip() or _default_url
TIMEOUT_SEC = int(os.getenv("CHARGE_CLIENT_TIMEOUT", "15"))



def send_charge_message(message: str, api_url: str = None) -> dict:
    url = (api_url or CHARGE_API_URL).rstrip("/")
    if not url.startswith("http"):
        url = "http://" + url
    if not url.endswith("/") and "/charge" not in url:
        url = url + "/"

    payload = {"message": (message or "").strip()}
    if not payload["message"]:
        return {"ok": False, "error": "메시지가 비어 있음", "duplicate": None}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            data = res.read().decode("utf-8")
            out = json.loads(data) if data.strip() else {}
            return {
                "ok": out.get("ok", False),
                "error": out.get("error"),
                "duplicate": out.get("duplicate"),
            }
    except urllib.error.HTTPError as e:
        try:
            body_err = e.read().decode("utf-8")
            err_data = json.loads(body_err)
            return {
                "ok": False,
                "error": err_data.get("error", f"HTTP {e.code}"),
                "duplicate": err_data.get("duplicate"),
            }
        except Exception:
            return {"ok": False, "error": f"HTTP {e.code} {e.reason}", "duplicate": None}
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e.reason), "duplicate": None}
    except Exception as e:
        return {"ok": False, "error": str(e), "duplicate": None}


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()

    text = text.strip()
    if not text:
        sys.exit(1)

    result = send_charge_message(text)
    if result["ok"]:
        print("OK – 자동 승인 처리되었습니다.")
    else:
        err = result.get("error") or "알 수 없는 오류"
        if result.get("duplicate"):
            print("중복 – 이미 처리된 메시지입니다.")
        else:
            print(f"실패 – {err}")
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
