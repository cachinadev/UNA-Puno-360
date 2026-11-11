$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = if (Test-Path services\api\.venv\Scripts\python.exe) {
  '.\services\api\.venv\Scripts\python.exe'
} elseif (Test-Path .venv\Scripts\python.exe) {
  '.\.venv\Scripts\python.exe'
} else {
  'python'
}
$env:PYTHONPATH = (Join-Path $root 'services\api')
& $python -m pytest -q services\api\tests tests
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas de backend.' }

if (Get-Command pnpm -ErrorAction SilentlyContinue) {
  pnpm -r typecheck
  if ($LASTEXITCODE -ne 0) { throw 'Falló TypeScript.' }
  pnpm --filter @una/web build
  if ($LASTEXITCODE -ne 0) { throw 'Falló el build web.' }
} elseif (Get-Command corepack -ErrorAction SilentlyContinue) {
  corepack pnpm -r typecheck
  if ($LASTEXITCODE -ne 0) { throw 'Falló TypeScript.' }
  corepack pnpm --filter @una/web build
  if ($LASTEXITCODE -ne 0) { throw 'Falló el build web.' }
} else {
  Write-Warning 'pnpm/Corepack no está instalado; se omitieron typecheck y build web.'
}
