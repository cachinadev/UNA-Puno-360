param([switch]$SkipDatabase)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Set-Location $root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 20 o superior no está instalado.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.10 o superior no está instalado.' }
$nodeMajor = [int]((node --version).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 20) { throw "Node.js 20+ es obligatorio; versión detectada: $(node --version)" }
$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]'3.10') { throw "Python 3.10+ es obligatorio; versión detectada: $pythonVersion" }

$envFile = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
  Copy-Item -LiteralPath (Join-Path $root '.env.example') -Destination $envFile
  Write-Warning 'Se creó .env. Configura la contraseña del usuario PostgreSQL local antes de preparar la base.'
}
Import-UnaEnvironment -Path $envFile -NativeDatabase

foreach ($secretName in @('AUTH_JWT_SECRET','COMMUNITY_JWT_SECRET','TRANSPORT_BRIDGE_TOKEN','TRANSPORT_WEBHOOK_SECRET')) {
  $current = [Environment]::GetEnvironmentVariable($secretName,'Process')
  if (-not $current -or $current.Length -lt 48 -or $current.StartsWith('replace_')) {
    Set-UnaDotEnvValue -Path $envFile -Name $secretName -Value (New-UnaSecret)
    Write-Host "Se generó un secreto local para $secretName (no se mostró en consola)." -ForegroundColor DarkGray
  }
}
$rawEnvironment = [System.IO.File]::ReadAllText($envFile)
if ($rawEnvironment -match '@db(?=[:/])') {
  [System.IO.File]::WriteAllText($envFile,($rawEnvironment -replace '@db(?=[:/])','@127.0.0.1'),[System.Text.UTF8Encoding]::new($false))
  Write-Host 'DATABASE_URL fue adaptado de db a 127.0.0.1 para desarrollo nativo.' -ForegroundColor DarkGray
}
Import-UnaEnvironment -Path $envFile -NativeDatabase

$venv = Join-Path $root 'services\api\.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
  & python -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear services/api/.venv.' }
}
$venvPython = Join-Path $venv 'Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'No se pudo actualizar pip.' }
& $venvPython -m pip install -r (Join-Path $root 'services\api\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de FastAPI.' }

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) { throw 'No se encontró pnpm ni Corepack.' }
  & corepack prepare pnpm@9.15.4 --activate
}
Invoke-UnaPnpm install

if (-not $SkipDatabase) {
  & (Join-Path $PSScriptRoot 'db-native.ps1') -StartService
  if ($LASTEXITCODE -ne 0) { throw 'La preparación de PostgreSQL/PostGIS no terminó correctamente.' }
}

Write-Host 'Preparación nativa terminada.' -ForegroundColor Green
Write-Host 'Comando principal: .\scripts\dev-native.ps1'
