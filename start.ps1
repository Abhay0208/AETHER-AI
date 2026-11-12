# AETHER start script for Windows (PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Port = $env:AETHER_PORT -as [int] -or 5467

$pidFile = Join-Path $Root "aether.pid"
if (Test-Path $pidFile) {
  $old = Get-Content $pidFile
  if (Get-Process -Id $old -ErrorAction SilentlyContinue) {
    Write-Host "AETHER already running (PID $old). Open: http://127.0.0.1:$Port"
    exit 0
  }
}

$venv = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venv)) {
  Write-Host "Backend venv not found. Run install.ps1 first." -ForegroundColor Red
  exit 1
}

Write-Host "Starting AETHER on http://127.0.0.1:$Port ..."
Start-Process "$venv" -ArgumentList "-m","app.main","--host","127.0.0.1","--port",$Port -WorkingDirectory "$Root\backend" -RedirectStandardOutput "$Root\server.log" -RedirectStandardError "$Root\server.log" -PassThru | Select-Object -ExpandProperty Id | Out-File $pidFile
Start-Sleep -Seconds 3

if (Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue) {
  Write-Host "AETHER running."
  Write-Host "UI:   http://127.0.0.1:$Port"
  Write-Host "API:  http://127.0.0.1:$Port/api"
  Write-Host "Docs: http://127.0.0.1:$Port/docs"
  Start-Process "http://127.0.0.1:$Port"
} else {
  Write-Host "Failed to start. See $Root\server.log" -ForegroundColor Red
  exit 1
}
