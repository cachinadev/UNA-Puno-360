param(
  [string]$ApiUrl,
  [string]$WebUrl,
  [switch]$SkipDatabase,
  [switch]$AllowStoppedServices
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
if (-not $ApiUrl) {
  $port = if ($env:API_PORT) { $env:API_PORT } else { '8000' }
  $ApiUrl = "http://127.0.0.1:$port"
}
if (-not $WebUrl) {
  $port = if ($env:WEB_PORT) { $env:WEB_PORT } else { '3000' }
  $WebUrl = "http://127.0.0.1:$port"
}
$results = New-Object System.Collections.Generic.List[object]
function Add-Result([string]$Name,[string]$Status,[string]$Detail) {
  $script:results.Add([pscustomobject]@{Check=$Name;Status=$Status;Detail=$Detail})
}

if (-not $SkipDatabase) {
  try {
    $config = Get-UnaDatabaseConfig
    $version = (Invoke-UnaPsql -Config $config -Database $config.Database -Query 'SELECT PostGIS_Version();' -TuplesOnly | Out-String).Trim()
    Add-Result 'PostgreSQL/PostGIS' 'PASS' $version
  } catch { Add-Result 'PostgreSQL/PostGIS' 'FAIL' $_.Exception.Message }
}

try {
  $health = Invoke-RestMethod "$ApiUrl/health" -TimeoutSec 10
  if ($health.status -eq 'ok') { Add-Result 'FastAPI /health' 'PASS' "PostGIS $($health.postgis)" } else { Add-Result 'FastAPI /health' 'FAIL' "status=$($health.status)" }
} catch { Add-Result 'FastAPI /health' ($(if($AllowStoppedServices){'SKIP'}else{'FAIL'})) $_.Exception.Message }

try {
  $swagger = Invoke-WebRequest "$ApiUrl/docs" -UseBasicParsing -TimeoutSec 10
  Add-Result 'Swagger' ($(if($swagger.StatusCode -eq 200){'PASS'}else{'FAIL'})) "HTTP $($swagger.StatusCode)"
} catch { Add-Result 'Swagger' ($(if($AllowStoppedServices){'SKIP'}else{'FAIL'})) $_.Exception.Message }

try {
  $web = Invoke-WebRequest $WebUrl -UseBasicParsing -TimeoutSec 15
  Add-Result 'Next.js' ($(if($web.StatusCode -eq 200){'PASS'}else{'FAIL'})) "HTTP $($web.StatusCode)"
} catch { Add-Result 'Next.js' ($(if($AllowStoppedServices){'SKIP'}else{'FAIL'})) $_.Exception.Message }

foreach ($check in @(
  @('Transporte',"$ApiUrl/transport/routes"),
  @('Geoespacial',"$ApiUrl/geo/places?limit=1"),
  @('Biblioteca',"$ApiUrl/library/branches?limit=1"),
  @('Comedor',"$ApiUrl/dining/menus?limit=1"),
  @('Servicios campus',"$ApiUrl/facilities/search?limit=1")
)) {
  try {
    $response = Invoke-WebRequest $check[1] -UseBasicParsing -TimeoutSec 10
    Add-Result $check[0] ($(if($response.StatusCode -eq 200){'PASS'}else{'FAIL'})) "HTTP $($response.StatusCode)"
  } catch { Add-Result $check[0] ($(if($AllowStoppedServices){'SKIP'}else{'FAIL'})) $_.Exception.Message }
}

foreach ($protected in @(@('Comunidad protegida',"$ApiUrl/community/feed"),@('Administración protegida',"$ApiUrl/admin/overview"))) {
  try {
    Invoke-WebRequest $protected[1] -UseBasicParsing -TimeoutSec 10 | Out-Null
    Add-Result $protected[0] 'FAIL' 'Aceptó una solicitud anónima.'
  } catch {
    $response = $_.Exception.Response
    if ($response -and $response.PSObject.Properties['StatusCode']) {
      $status = [int]$response.StatusCode
      if ($status -in @(401,503)) { Add-Result $protected[0] 'PASS' "HTTP $status" }
      else { Add-Result $protected[0] 'FAIL' $_.Exception.Message }
    } elseif ($AllowStoppedServices) { Add-Result $protected[0] 'SKIP' $_.Exception.Message }
    else { Add-Result $protected[0] 'FAIL' $_.Exception.Message }
  }
}

$results | Format-Table -AutoSize -Wrap
$failed = @($results | Where-Object Status -eq 'FAIL')
if ($failed.Count -gt 0) { throw "$($failed.Count) comprobaciones fallaron." }
