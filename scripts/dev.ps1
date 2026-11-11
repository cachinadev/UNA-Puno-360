param([switch]$WithoutDocker)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path .env)) { throw 'Falta .env. Ejecuta .\scripts\setup.ps1 primero.' }
if ($WithoutDocker) {
  Write-Host 'Inicia la API y la web en terminales separadas:'
  Write-Host '.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services\api --reload --port 8000'
  Write-Host 'corepack pnpm --filter @una/web dev'
  exit 0
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop no está disponible. Usa -WithoutDocker para ver comandos manuales.' }
docker compose up --build
