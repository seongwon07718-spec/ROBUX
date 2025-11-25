try:
    ...
except (requests.RequestException, ValueError, KeyError):
    return 0
except Exception:
    return 0
