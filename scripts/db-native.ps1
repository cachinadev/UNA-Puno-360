param(
  [switch]$StartService,
  [switch]$SkipCreate,
  [switch]$CheckOnly,
  [switch]$RepairRole,
  [string]$AdminUser='postgres'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib\Native.ps1')
Import-UnaEnvironment -Path (Join-Path $root '.env') -NativeDatabase
$config = Get-UnaDatabaseConfig

$psql = Find-PostgresTool -Name 'psql'
if (-not $psql) {
  throw 'PostgreSQL no está instalado o psql no está en PATH. Instala PostgreSQL para Windows y PostGIS antes de continuar.'
}
Write-Host "psql: $psql" -ForegroundColor DarkGray

$isLocal = $config.Host -in @('127.0.0.1','localhost','::1')
if ($isLocal) {
  $services = @(Get-PostgresWindowsServices)
  if ($services.Count -eq 0) {
    Write-Warning 'No se detectó un servicio Windows de PostgreSQL. Se intentará conectar por si usas una instancia portátil o administrada manualmente.'
  } else {
    foreach ($service in $services) {
      if ($service.Status -ne 'Running') {
        if ($StartService) {
          try {
            Write-Host "Iniciando servicio $($service.Name)..."
            Start-Service -Name $service.Name -ErrorAction Stop
            $service.WaitForStatus('Running',[TimeSpan]::FromSeconds(20))
          } catch {
            throw "No se pudo iniciar $($service.Name). Abre PowerShell como administrador o inicia el servicio desde services.msc. $($_.Exception.Message)"
          }
        } else {
          throw "El servicio PostgreSQL '$($service.Name)' está detenido. Ejecuta este script con -StartService o inícialo desde services.msc."
        }
      }
      Write-Host "Servicio PostgreSQL: $($service.Name) ($($service.Status))" -ForegroundColor Green
    }
  }
}

if ($RepairRole) {
  $python = Join-Path $root 'services\api\.venv\Scripts\python.exe'
  if (-not (Test-Path -LiteralPath $python)) { throw 'Falta services/api/.venv. Ejecuta setup-native.ps1 -SkipDatabase primero.' }
  $maintenance = if ($env:POSTGRES_MAINTENANCE_DB) { $env:POSTGRES_MAINTENANCE_DB } else { 'postgres' }
  & $python (Join-Path $PSScriptRoot 'repair-db-role.py') --admin-user $AdminUser --maintenance-db $maintenance
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo reparar el rol PostgreSQL.' }
}

$databaseExists = $false
try {
  $null = Invoke-UnaPsql -Config $config -Database $config.Database -Query 'SELECT 1;' -TuplesOnly
  $databaseExists = $true
} catch {
  Write-Host "La base '$($config.Database)' todavía no acepta conexiones; verificando el servidor..." -ForegroundColor Yellow
}

if (-not $databaseExists) {
  $maintenance = if ($env:POSTGRES_MAINTENANCE_DB) { $env:POSTGRES_MAINTENANCE_DB } else { 'postgres' }
  try {
    $null = Invoke-UnaPsql -Config $config -Database $maintenance -Query 'SELECT current_user;' -TuplesOnly
  } catch {
    throw "PostgreSQL responde en $($config.Host):$($config.Port), pero rechazó el rol '$($config.User)' o su contraseña de DATABASE_URL. No pruebes usuarios distintos manualmente: ejecuta '.\scripts\db-native.ps1 -StartService -RepairRole' y proporciona la contraseña del superusuario PostgreSQL cuando se solicite."
  }
  $databaseLiteral = ConvertTo-SqlLiteral $config.Database
  $exists = (Invoke-UnaPsql -Config $config -Database $maintenance -Query "SELECT 1 FROM pg_database WHERE datname=$databaseLiteral;" -TuplesOnly | Out-String).Trim()
  if ($exists -ne '1') {
    if ($SkipCreate -or $CheckOnly) { throw "La base '$($config.Database)' no existe y la creación está deshabilitada." }
    if ($config.Database -notmatch '^[A-Za-z0-9_.-]+$') { throw 'El nombre de base contiene caracteres no admitidos por el creador nativo.' }
    $createdb = Find-PostgresTool -Name 'createdb'
    if (-not $createdb) { throw 'No se encontró createdb junto a psql.' }
    $oldPassword = $env:PGPASSWORD
    try {
      $env:PGPASSWORD = $config.Password
      & $createdb '-w' '-h' $config.Host '-p' ([string]$config.Port) '-U' $config.User $config.Database
      if ($LASTEXITCODE -ne 0) { throw "El usuario '$($config.User)' no pudo crear la base. Solicita el privilegio CREATEDB o pide al administrador que cree '$($config.Database)'." }
    } finally { $env:PGPASSWORD = $oldPassword }
    Write-Host "Base creada: $($config.Database)" -ForegroundColor Green
  }
}

$available = (Invoke-UnaPsql -Config $config -Database $config.Database -Query "SELECT default_version FROM pg_available_extensions WHERE name='postgis';" -TuplesOnly | Out-String).Trim()
if (-not $available) {
  throw 'PostGIS no está instalado para esta instancia de PostgreSQL. Instálalo con StackBuilder o el instalador oficial compatible con tu versión de PostgreSQL.'
}
Write-Host "PostGIS disponible: $available" -ForegroundColor Green
if ($CheckOnly) {
  $installed = (Invoke-UnaPsql -Config $config -Database $config.Database -Query "SELECT extversion FROM pg_extension WHERE extname='postgis';" -TuplesOnly | Out-String).Trim()
  if (-not $installed) { throw 'PostGIS está disponible pero la extensión aún no está habilitada en la base.' }
  Write-Host "PostGIS habilitado: $installed" -ForegroundColor Green
  exit 0
}

$ledgerSql = @'
CREATE TABLE IF NOT EXISTS una_schema_migrations (
  filename TEXT PRIMARY KEY,
  checksum_sha256 TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
'@
$null = Invoke-UnaPsql -Config $config -Database $config.Database -Query $ledgerSql
$migrationRoot = Join-Path $root 'services\api\sql'
$migrations = @(Get-ChildItem -LiteralPath $migrationRoot -Filter '*.sql' -File | Sort-Object Name)
if ($migrations.Count -eq 0) { throw "No se encontraron migraciones en $migrationRoot" }

foreach ($migration in $migrations) {
  $checksum = (Get-FileHash -LiteralPath $migration.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  $fileLiteral = ConvertTo-SqlLiteral $migration.Name
  $record = (Invoke-UnaPsql -Config $config -Database $config.Database -Query "SELECT checksum_sha256 FROM una_schema_migrations WHERE filename=$fileLiteral;" -TuplesOnly | Out-String).Trim()
  if ($record) {
    if ($record -ne $checksum) { throw "La migración aplicada '$($migration.Name)' cambió en disco. No se reaplicó para proteger los datos." }
    Write-Host "Ya aplicada: $($migration.Name)" -ForegroundColor DarkGray
    continue
  }
  Write-Host "Aplicando: $($migration.Name)"
  $checksumLiteral = ConvertTo-SqlLiteral $checksum
  $transactionFile = [System.IO.Path]::GetTempFileName()
  try {
    $migrationSql = [System.IO.File]::ReadAllText($migration.FullName)
    $ledgerInsert = "`r`nINSERT INTO una_schema_migrations(filename,checksum_sha256) VALUES ($fileLiteral,$checksumLiteral);`r`n"
    [System.IO.File]::WriteAllText($transactionFile,$migrationSql+$ledgerInsert,[System.Text.UTF8Encoding]::new($false))
    $null = Invoke-UnaPsql -Config $config -Database $config.Database -File $transactionFile
  } catch {
    throw "Falló la migración '$($migration.Name)'. La transacción fue revertida. Si es 001_init.sql, verifica privilegios CREATE EXTENSION para PostGIS. $($_.Exception.Message)"
  } finally { Remove-Item -LiteralPath $transactionFile -Force -ErrorAction SilentlyContinue }
}

$postgisVersion = (Invoke-UnaPsql -Config $config -Database $config.Database -Query 'SELECT PostGIS_Version();' -TuplesOnly | Out-String).Trim()
$migrationCount = (Invoke-UnaPsql -Config $config -Database $config.Database -Query 'SELECT count(*) FROM una_schema_migrations;' -TuplesOnly | Out-String).Trim()
Write-Host "Base lista: $($config.Database), PostGIS $postgisVersion, migraciones registradas: $migrationCount" -ForegroundColor Green
