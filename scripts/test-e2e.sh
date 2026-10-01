#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# BASE_URL permet de réutiliser ces tests contre Docker ou la VM réelle.
if [[ -n "${BASE_URL:-}" ]]; then
  python scripts/wait-http.py "${BASE_URL%/}/health"
  exec python -m pytest tests/e2e -q
fi

port="${E2E_PORT:-8092}"
export BASE_URL="http://127.0.0.1:$port"
export APP_VERSION="${APP_VERSION:-local}"
export EXPECTED_VERSION="$APP_VERSION"
server_log="$(mktemp)"
python -m gunicorn --bind "127.0.0.1:$port" --workers 1 --no-control-socket app:app >"$server_log" 2>&1 &
server_pid=$!
cleanup() {
  kill "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
  cat "$server_log"
  rm -f "$server_log"
}
trap cleanup EXIT
python scripts/wait-http.py "$BASE_URL/health"
# Un port déjà occupé ne doit jamais permettre de tester le mauvais serveur.
kill -0 "$server_pid"
python -m pytest tests/e2e -q
