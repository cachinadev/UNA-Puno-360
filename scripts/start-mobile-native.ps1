param(
  [ValidateSet('lan','localhost','tunnel')][string]$Connection='lan',
  [switch]$AndroidEmulator,
  [string]$ApiUrl
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
Set-Location $root
$apiPort = if ($env:API_PORT) { [int]$env:API_PORT } else { 8000 }
if ($ApiUrl) {
  $env:EXPO_PUBLIC_API_URL = $ApiUrl
} elseif ($Connection -eq 'localhost') {
  $env:EXPO_PUBLIC_API_URL = "http://10.0.2.2:$apiPort"
} else {
  $lan = Get-UnaLanAddress
  if (-not $lan) { throw 'No se pudo determinar una IPv4 LAN. Configura EXPO_PUBLIC_API_URL manualmente.' }
  $env:EXPO_PUBLIC_API_URL = "http://$lan`:$apiPort"
}
Write-Host "Expo usará API: $($env:EXPO_PUBLIC_API_URL)" -ForegroundColor Cyan
$arguments = @('--filter','@una/mobile','start','--','--' + $Connection)
if ($AndroidEmulator) { $arguments += '--android' }
Invoke-UnaPnpm @arguments
