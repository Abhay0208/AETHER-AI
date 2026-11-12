# AETHER installer for Windows (PowerShell).
# Requires: Python 3.10+, Node.js 18+, FFmpeg, Git.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Port = $env:AETHER_PORT -as [int] -or 5467

Write-Host "=== AETHER Windows Installer ==="
Write-Host "Root: $Root"

function Test-Cmd($name) { Get-Command $name -ErrorAction SilentlyContinue -is [System.Management.Automation.CommandInfo] }

$missing = @()
foreach ($cmd in @("python","node","npm","ffmpeg","git")) {
  if (-not (Test-Cmd $cmd)) { $missing += $cmd }
}
if ($missing.Count -gt 0) {
  Write-Host "Missing dependencies: $($missing -join ', ')" -ForegroundColor Yellow
  Write-Host "Install them manually, then re-run this script."
  exit 1
}

Write-Host "[1/3] Creating Python virtual environment..."
python -m venv "$Root\backend\.venv"
& "$Root\backend\.venv\Scripts\pip.exe" install --upgrade pip
& "$Root\backend\.venv\Scripts\pip.exe" install -r "$Root\backend\requirements.txt"

Write-Host "[2/3] Initializing database..."
& "$Root\backend\.venv\Scripts\python.exe" - <<'PY'
import sys
sys.path.insert(0, "app")
from database import init_schema
from config import ensure_dirs
ensure_dirs()
init_schema()
print("Database initialized.")
PY

Write-Host "[3/3] Building frontend..."
Set-Location "$Root\frontend"
npm install
npm run build
Set-Location "$Root"

Write-Host "Installation complete."
Write-Host "Run: .\start.ps1"
Write-Host "Open: http://127.0.0.1:$Port"
