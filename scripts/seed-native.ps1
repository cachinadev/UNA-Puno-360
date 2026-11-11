param([switch]$SkipDatabaseCheck)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
if (-not $SkipDatabaseCheck) { & (Join-Path $PSScriptRoot 'db-native.ps1') -StartService }

$apiRoot = Join-Path $root 'services\api'
$python = Join-Path $apiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta services/api/.venv. Ejecuta setup-native.ps1.' }

Push-Location $apiRoot
try {
  & $python -m app.community_cli seed-demo
  if ($LASTEXITCODE -ne 0) { throw 'Falló la semilla de comunidad.' }
  & $python -m app.facility_cli seed-demo
  if ($LASTEXITCODE -ne 0) { throw 'Falló la semilla de instalaciones.' }
  foreach ($kind in @('branches','books','locations','menus','announcements')) {
    & $python -c "from app.import_services import import_csv; print(import_csv('$kind','examples/$kind.demo.csv'))"
    if ($LASTEXITCODE -ne 0) { throw "Falló la importación demo: $kind" }
  }
  & $python -m app.mvp_seed
  if ($LASTEXITCODE -ne 0) { throw 'Falló la semilla interactiva del MVP.' }
} finally { Pop-Location }

$config = Get-UnaDatabaseConfig
$null = Invoke-UnaPsql -Config $config -Database $config.Database -File (Join-Path $apiRoot 'examples\transport.demo.sql')
Write-Host 'Datos de DEMOSTRACIÓN cargados. No representan información oficial ni GPS real.' -ForegroundColor Yellow
