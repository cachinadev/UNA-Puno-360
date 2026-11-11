param([string]$HostOverride,[int]$PortOverride=0)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
$apiRoot = Join-Path $root 'services\api'
$python = Join-Path $apiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta services/api/.venv. Ejecuta .\scripts\setup-native.ps1.' }
$hostName = if ($HostOverride) { $HostOverride } elseif ($env:API_HOST) { $env:API_HOST } else { '127.0.0.1' }
$port = if ($PortOverride -gt 0) { $PortOverride } elseif ($env:API_PORT) { [int]$env:API_PORT } else { 8000 }
Set-Location $apiRoot
Write-Host "FastAPI: http://$hostName`:$port (app.main:app)" -ForegroundColor Cyan
& $python -m uvicorn app.main:app --host $hostName --port $port --reload
exit $LASTEXITCODE
