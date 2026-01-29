#!/usr/bin/env bash
set -euo pipefail

APP_HOST="127.0.0.1"
APP_PORT="9000"
PUBLIC_HTTP_PORT="8000"
OPTIONS_FILE="/data/options.json"

read_option() {
  local key=$1
  if [ -f "$OPTIONS_FILE" ] && command -v jq >/dev/null 2>&1; then
    jq -r ".${key} // empty" "$OPTIONS_FILE" 2>/dev/null || true
  else
    echo ""
  fi
}

HTTPS_ENABLED=${HTTPS_ENABLED:-$(read_option "https_enabled")}
HTTPS_DOMAIN=${HTTPS_DOMAIN:-$(read_option "https_domain")}
HTTPS_EMAIL=${HTTPS_EMAIL:-$(read_option "https_email")}

if [ -z "$HTTPS_ENABLED" ]; then
  HTTPS_ENABLED="false"
fi

shopt -s nocasematch
if [[ "$HTTPS_ENABLED" == "true" || "$HTTPS_ENABLED" == "1" || "$HTTPS_ENABLED" == "yes" ]]; then
  HTTPS_ENABLED="true"
else
  HTTPS_ENABLED="false"
fi
shopt -u nocasematch

HTTPS_DOMAIN=$(echo -n "${HTTPS_DOMAIN:-}" | xargs || true)
HTTPS_EMAIL=$(echo -n "${HTTPS_EMAIL:-}" | xargs || true)

export APP_HOST APP_PORT PUBLIC_HTTP_PORT
export ENABLE_HTTPS="$HTTPS_ENABLED"
export E_FACE_DOMAIN="${HTTPS_DOMAIN:-}"
export E_FACE_TLS_EMAIL="${HTTPS_EMAIL:-}"

python3 /app/backend/scripts/render_caddyfile.py

uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" &
UVICORN_PID=$!

caddy run --config /app/backend/runtime/Caddyfile --watch &
CADDY_PID=$!

cleanup() {
  kill "$UVICORN_PID" "$CADDY_PID" 2>/dev/null || true
  wait "$UVICORN_PID" "$CADDY_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait -n "$UVICORN_PID" "$CADDY_PID"
