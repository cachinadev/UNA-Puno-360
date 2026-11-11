param([switch]$SkipE2E,[switch]$SkipMobile,[switch]$LiveApi)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
Set-Location $root
$python = Join-Path $root 'services\api\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta services/api/.venv. Ejecuta setup-native.ps1.' }

$env:PYTHONPATH = (Join-Path $root 'services\api')
$databaseReady = $false
try {
  $config = Get-UnaDatabaseConfig
  $null = Invoke-UnaPsql -Config $config -Database $config.Database -Query 'SELECT PostGIS_Version();' -TuplesOnly
  $databaseReady = $true
} catch { Write-Warning "Pruebas PostGIS omitidas: $($_.Exception.Message)" }
if ($databaseReady) { $env:RUN_DB_TESTS='1' } else { Remove-Item Env:RUN_DB_TESTS -ErrorAction SilentlyContinue }
& $python -m pytest -q services\api\tests tests
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas de backend.' }

Invoke-UnaPnpm -r typecheck
Invoke-UnaPnpm --filter '@una/web' build
Invoke-UnaPnpm --filter '@una/web' test
if (-not $SkipMobile) { Invoke-UnaPnpm --filter '@una/mobile' exec expo export --platform android }
if (-not $SkipE2E) { Invoke-UnaPnpm --filter '@una/web' e2e }
if ($LiveApi) {
  $apiPort = if ($env:API_PORT) { $env:API_PORT } else { '8000' }
  & $python (Join-Path $PSScriptRoot 'native-api-smoke.py') --base-url "http://127.0.0.1:$apiPort"
  if ($LASTEXITCODE -ne 0) { throw 'Falló el recorrido API nativo.' }
}
Write-Host 'Validación nativa terminada.' -ForegroundColor Green
