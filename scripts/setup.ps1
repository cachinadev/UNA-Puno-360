$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 20 o superior no está instalado.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.10 o superior no está instalado.' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Warning 'Se creó .env. Reemplaza todos los secretos antes de iniciar.' }

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) { throw 'No se encontró pnpm ni Corepack.' }
  corepack prepare pnpm@9.15.4 --activate
  corepack pnpm install
} else {
  pnpm install
}

if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r services\api\requirements.txt
Write-Host 'Preparación terminada. Revisa .env y ejecuta .\scripts\dev.ps1' -ForegroundColor Green
