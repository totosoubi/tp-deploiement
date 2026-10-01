import json
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8080/health", timeout=2) as response:
    if response.status != 200 or json.load(response) != {"status": "ok"}:
        raise SystemExit("Healthcheck en échec")
