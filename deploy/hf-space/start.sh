#!/usr/bin/env bash
# Starts Ollama, the backend and Caddy; if any of them stops, the Space restarts.
set -euo pipefail

if [[ -z "${COACH_PASSWORD:-}" ]]; then
  echo "Set the COACH_PASSWORD secret in the Space settings (and optionally COACH_USER)." >&2
  exit 1
fi
export COACH_USER="${COACH_USER:-coach}"
COACH_PASSWORD_HASH="$(caddy hash-password --plaintext "$COACH_PASSWORD")"
export COACH_PASSWORD_HASH
unset COACH_PASSWORD

ollama serve &
for _ in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &

wait -n
exit 1
