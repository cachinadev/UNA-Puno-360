param(
  [switch]$SkipDatabaseSetup,
  [switch]$Mobile,
  [switch]$AndroidEmulator,
  [switch]$PhysicalDevice
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
$envFile = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Falta .env. Ejecuta .\scripts\setup-native.ps1 primero.' }
Import-UnaEnvironment -Path $envFile -NativeDatabase

if (-not $SkipDatabaseSetup) {
  & (Join-Path $PSScriptRoot 'db-native.ps1') -StartService
  if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL/PostGIS no está listo.' }
}

$apiPort = if ($env:API_PORT) { [int]$env:API_PORT } else { 8000 }
$webPort = if ($env:WEB_PORT) { [int]$env:WEB_PORT } else { 3000 }
$shell = (Get-Process -Id $PID).Path
$apiScript = Join-Path $PSScriptRoot 'start-api-native.ps1'
$webScript = Join-Path $PSScriptRoot 'start-web-native.ps1'
$apiHost = if ($PhysicalDevice) { '0.0.0.0' } elseif ($env:API_HOST) { $env:API_HOST } else { '127.0.0.1' }

if ($PhysicalDevice) {
  $lan = Get-UnaLanAddress
  if (-not $lan) { throw 'No se encontró una IPv4 LAN para el dispositivo físico.' }
  Write-Warning "La API escuchará en la LAN ($lan). Este script NO modifica el firewall; autoriza Python manualmente solo en una red privada si Windows lo solicita."
}

if (Test-UnaPort -Port $apiPort) {
  Write-Warning "El puerto API $apiPort ya está ocupado; no se abrió otra API."
} else {
  Start-Process -FilePath $shell -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-File',('"'+$apiScript+'"'),'-HostOverride',$apiHost,'-PortOverride',[string]$apiPort)
}
if (Test-UnaPort -Port $webPort) {
  Write-Warning "El puerto web $webPort ya está ocupado; no se abrió otra web."
} else {
  Start-Process -FilePath $shell -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-File',('"'+$webScript+'"'),'-PortOverride',[string]$webPort)
}

if ($Mobile) {
  $mobileScript = Join-Path $PSScriptRoot 'start-mobile-native.ps1'
  $mobileArgs = @('-NoExit','-ExecutionPolicy','Bypass','-File',('"'+$mobileScript+'"'))
  if ($AndroidEmulator) { $mobileArgs += @('-Connection','localhost','-AndroidEmulator') }
  elseif ($PhysicalDevice) { $mobileArgs += @('-Connection','lan','-ApiUrl',("http://$lan`:$apiPort")) }
  else { $mobileArgs += @('-Connection','lan') }
  Start-Process -FilePath $shell -ArgumentList $mobileArgs
}

Write-Host 'Procesos nativos iniciados en ventanas separadas.' -ForegroundColor Green
Write-Host "Web:     http://localhost:$webPort"
Write-Host "API:     http://localhost:$apiPort"
Write-Host "Swagger: http://localhost:$apiPort/docs"
Write-Host 'Cuando estén listos: .\scripts\health-check.ps1'
