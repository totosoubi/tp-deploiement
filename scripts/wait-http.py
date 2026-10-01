import json
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

opener = build_opener(ProxyHandler({}))
url = sys.argv[1]
deadline = time.monotonic() + 45
while True:
    try:
        with opener.open(url, timeout=3) as response:
            if response.status == 200 and json.load(response) == {"status": "ok"}:
                print("Healthcheck HTTP réussi.")
                break
    except (URLError, OSError, ValueError):
        pass
    if time.monotonic() >= deadline:
        raise SystemExit("L'application ne répond pas correctement au healthcheck.")
    time.sleep(1)
