#!/usr/bin/env bash
# Start AETHER server (assumes install.sh has been run).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${AETHER_PORT:-5467}"

cd "$ROOT_DIR"

if [ -f "$ROOT_DIR/aether.pid" ] && kill -0 "$(cat "$ROOT_DIR/aether.pid")" 2>/dev/null; then
  echo "AETHER already running (PID $(cat "$ROOT_DIR/aether.pid"))."
  echo "Open: http://127.0.0.1:$PORT"
  exit 0
fi

echo "Starting AETHER on http://127.0.0.1:$PORT ..."
cd "$ROOT_DIR/backend"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
  echo "Backend venv not found. Run ./install.sh first." >&2
  exit 1
fi
nohup "$VENV_PYTHON" -u -m app.main > "$ROOT_DIR/server.log" 2>&1 &
echo $! > "$ROOT_DIR/aether.pid"
sleep 2

if kill -0 "$(cat "$ROOT_DIR/aether.pid")" 2>/dev/null; then
  echo "AETHER running (PID $(cat "$ROOT_DIR/aether.pid"))."
  echo "UI:      http://127.0.0.1:$PORT"
  echo "API:     http://127.0.0.1:$PORT/api"
  echo "Docs:    http://127.0.0.1:$PORT/docs"
  echo "Logs:    $ROOT_DIR/server.log"
  if [ -d /data/data/com.termux ]; then
    termux-open-url "http://127.0.0.1:$PORT" 2>/dev/null || true
  elif command -v xdg-open >/dev/null; then
    xdg-open "http://127.0.0.1:$PORT" 2>/dev/null || true
  elif command -v open >/dev/null; then
    open "http://127.0.0.1:$PORT" 2>/dev/null || true
  fi
else
  echo "Failed to start. See $ROOT_DIR/server.log"
  exit 1
fi
