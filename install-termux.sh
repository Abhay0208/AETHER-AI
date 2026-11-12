#!/usr/bin/env bash
# AETHER installer for Android Termux.
# Tested independently on Termux (aarch64).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AETHER_DATA_DIR="${AETHER_DATA_DIR:-$ROOT_DIR/data}"

echo "=== AETHER Termux Installer ==="
echo "Root: $ROOT_DIR"
echo "Data dir: $AETHER_DATA_DIR"

termux-setup-storage 2>/dev/null || true

echo "[1/4] Installing system packages..."
pkg update -y
pkg install -y python nodejs ffmpeg git clang make

echo "[2/4] Running main installer..."
bash "$ROOT_DIR/install.sh"

echo "[3/4] Creating app shortcut..."
cat > "$HOME/aether-start.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
cd "$ROOT_DIR"
bash start.sh
EOF
chmod +x "$HOME/aether-start.sh"

echo "[4/4] Done."
echo "Run:  bash $HOME/aether-start.sh"
echo "Open: http://127.0.0.1:5467"
echo "Note: On Android, long-running background work may be restricted by battery optimization."
