#!/usr/bin/env bash
# AETHER installer — Linux (incl. Termux on Android) and macOS.
# Usage: curl -fsSL install.sh | bash   or   ./install.sh
set -euo pipefail

APP_NAME="AETHER"
PORT="${AETHER_PORT:-5467}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_FILE="$ROOT_DIR/install.log"

log() { echo "[AETHER] $*" | tee -a "$LOG_FILE"; }
err() { echo "[AETHER ERROR] $*" | tee -a "$LOG_FILE" >&2; }

: > "$LOG_FILE"
log "Starting $APP_NAME installer"
log "Root directory: $ROOT_DIR"

# ---------------------------------------------------------------------------
# 1. Detect environment
# ---------------------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
IS_TERMUX="false"
if [ -d /data/data/com.termux ]; then IS_TERMUX="true"; fi

log "OS=$OS ARCH=$ARCH TERMUX=$IS_TERMUX"

RAM_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
RAM_GB=$(( RAM_KB / 1024 / 1024 ))
log "RAM ≈ ${RAM_GB} GB"

# ---------------------------------------------------------------------------
# 2. Dependency helpers
# ---------------------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

install_pkg_linux() {
  # Try apt, then apk (Alpine), then pkg (Termux).
  if have apt-get; then
    sudo apt-get update -y && sudo apt-get install -y "$@" || { err "apt install failed"; return 1; }
  elif have apk; then
    sudo apk add --no-cache "$@" || { err "apk install failed"; return 1; }
  elif have pkg; then
    pkg install -y "$@" || { err "pkg install failed"; return 1; }
  else
    err "No supported package manager found. Install manually: $*"
    return 1
  fi
}

ensure_cmd() {
  local name="$1" install_name="${2:-$1}"
  if have "$name"; then
    log "OK: $name already installed ($(command -v "$name"))"
    return 0
  fi
  log "Installing $install_name..."
  case "$OS" in
    Linux)
      if [ "$IS_TERMUX" = "true" ]; then
        pkg update -y && pkg install -y "$install_name"
      else
        install_pkg_linux "$install_name"
      fi
      ;;
    Darwin)
      if have brew; then brew install "$install_name"; else err "Homebrew required on macOS"; return 1; fi
      ;;
    *) err "Unsupported OS: $OS"; return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# 3. System dependencies
# ---------------------------------------------------------------------------
log "Checking system dependencies..."
ensure_cmd python3 python3 || true
ensure_cmd python3-dev python3-dev 2>/dev/null || true
ensure_cmd pip3 python3-pip 2>/dev/null || true
ensure_cmd node nodejs 2>/dev/null || true
ensure_cmd npm nodejs 2>/dev/null || true
ensure_cmd ffmpeg ffmpeg 2>/dev/null || true
ensure_cmd git git 2>/dev/null || true

# Build tools for native Python packages (cryptography etc.)
if [ "$IS_TERMUX" = "true" ]; then
  pkg install -y clang make python-dev 2>/dev/null || log "Note: could not install build tools (may be fine with wheels)"
elif have apt-get; then
  sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev 2>/dev/null || log "Note: build tools install skipped"
fi

python3 --version
node --version
ffmpeg -version | head -1

# ---------------------------------------------------------------------------
# 4. Python backend
# ---------------------------------------------------------------------------
log "Setting up Python backend..."
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi
# shellcheck disable=SC1091
source "$BACKEND_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

# Initialize the database once.
cd "$BACKEND_DIR"
python - <<'PY'
import sys
sys.path.insert(0, "app")
from database import init_schema
from config import ensure_dirs
ensure_dirs()
init_schema()
print("Database initialized.")
PY

# ---------------------------------------------------------------------------
# 5. Frontend
# ---------------------------------------------------------------------------
log "Setting up frontend..."
cd "$FRONTEND_DIR"
if [ ! -d node_modules ]; then
  npm install
fi
npm run build
log "Frontend built."

# ---------------------------------------------------------------------------
# 6. Start the server
# ---------------------------------------------------------------------------
cd "$ROOT_DIR"
log "Starting AETHER server on http://127.0.0.1:$PORT ..."
if [ -f "$ROOT_DIR/aether.pid" ] && kill -0 "$(cat "$ROOT_DIR/aether.pid")" 2>/dev/null; then
  log "AETHER already running (PID $(cat "$ROOT_DIR/aether.pid"))."
else
  cd "$BACKEND_DIR"
  nohup python -u -m app.main > "$ROOT_DIR/server.log" 2>&1 &
  echo $! > "$ROOT_DIR/aether.pid"
  sleep 2
  if kill -0 "$(cat "$ROOT_DIR/aether.pid")" 2>/dev/null; then
    log "AETHER running (PID $(cat "$ROOT_DIR/aether.pid")). Log: $ROOT_DIR/server.log"
  else
    err "Server failed to start. See $ROOT_DIR/server.log"
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 7. Open browser
# ---------------------------------------------------------------------------
URL="http://127.0.0.1:$PORT"
log "Open $URL in your browser."
if [ "$IS_TERMUX" = "true" ]; then
  termux-open-url "$URL" 2>/dev/null || log "Run: termux-open-url $URL"
elif [ "$OS" = "Darwin" ]; then
  open "$URL" 2>/dev/null || true
elif have xdg-open; then
  xdg-open "$URL" 2>/dev/null || true
fi

log "Installation complete."
log "Start anytime with: ./start.sh"
log "Stop with: kill \$(cat aether.pid)"
