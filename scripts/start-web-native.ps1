param([int]$PortOverride=0)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
Set-Location $root
$port = if ($PortOverride -gt 0) { $PortOverride } elseif ($env:WEB_PORT) { [int]$env:WEB_PORT } else { 3000 }
Write-Host "Next.js: http://127.0.0.1:$port" -ForegroundColor Cyan
Invoke-UnaPnpm --filter '@una/web' dev -- --hostname 127.0.0.1 --port ([string]$port)
