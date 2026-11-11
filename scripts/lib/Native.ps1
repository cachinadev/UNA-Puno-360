Set-StrictMode -Version Latest

function Import-UnaEnvironment {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [switch]$NativeDatabase
  )
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "No existe el archivo de entorno: $Path"
  }
  foreach ($line in [System.IO.File]::ReadAllLines((Resolve-Path -LiteralPath $Path))) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
    if ($trimmed -notmatch '^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { continue }
    $name = $matches[1]
    $value = $matches[2].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1,$value.Length-2)
    }
    [Environment]::SetEnvironmentVariable($name,$value,'Process')
  }
  if ($NativeDatabase -and $env:DATABASE_URL) {
    $nativeHost = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { '127.0.0.1' }
    $env:DATABASE_URL = $env:DATABASE_URL -replace '@db(?=[:/])',("@"+$nativeHost)
  }
  if (-not $env:CORS_ORIGINS -and $env:WEB_ORIGIN) { $env:CORS_ORIGINS = $env:WEB_ORIGIN }
}

function Set-UnaDotEnvValue {
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$Name,[Parameter(Mandatory=$true)][string]$Value)
  $lines = [System.Collections.Generic.List[string]]::new()
  $found = $false
  foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
    if ($line -match ('^\s*' + [regex]::Escape($Name) + '\s*=')) {
      $lines.Add("$Name=$Value"); $found=$true
    } else { $lines.Add($line) }
  }
  if (-not $found) { $lines.Add("$Name=$Value") }
  [System.IO.File]::WriteAllLines($Path,$lines,[System.Text.UTF8Encoding]::new($false))
}

function New-UnaSecret {
  param([int]$Bytes=48)
  $buffer = New-Object byte[] $Bytes
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
  return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Invoke-UnaPnpm {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PnpmArgs)
  if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    & pnpm @PnpmArgs
  } elseif (Get-Command corepack -ErrorAction SilentlyContinue) {
    & corepack pnpm @PnpmArgs
  } else {
    throw 'No se encontró pnpm ni Corepack. Instala Node.js 20 o superior.'
  }
  if ($LASTEXITCODE -ne 0) { throw "pnpm terminó con código $LASTEXITCODE" }
}

function Find-PostgresTool {
  param([Parameter(Mandatory=$true)][string]$Name)
  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
  $roots = @()
  if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles 'PostgreSQL') }
  if (${env:ProgramFiles(x86)}) { $roots += (Join-Path ${env:ProgramFiles(x86)} 'PostgreSQL') }
  foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    $candidate = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
      Sort-Object { try { [version]$_.Name } catch { [version]'0.0' } } -Descending |
      ForEach-Object { Join-Path $_.FullName ("bin\$Name.exe") } |
      Where-Object { Test-Path -LiteralPath $_ } |
      Select-Object -First 1
    if ($candidate) { return $candidate }
  }
  return $null
}

function Get-UnaDatabaseConfig {
  if (-not $env:DATABASE_URL) { throw 'DATABASE_URL no está configurado en .env.' }
  $pattern = '^postgres(?:ql)?://(?<userinfo>[^@]+)@(?<host>\[[^\]]+\]|[^:/]+)(?::(?<port>\d+))?/(?<database>[^?]+)'
  if ($env:DATABASE_URL -notmatch $pattern) {
    throw 'DATABASE_URL debe usar el formato postgresql://usuario:clave@host:puerto/base.'
  }
  $userinfo = @($matches['userinfo'].Split(':',2))
  if ($userinfo.Count -ne 2) { throw 'DATABASE_URL debe incluir usuario y contraseña codificados como URL.' }
  $hostName = $matches['host'].Trim('[',']')
  $port = if ($matches['port']) { [int]$matches['port'] } else { 5432 }
  [pscustomobject]@{
    Host = [Uri]::UnescapeDataString($hostName)
    Port = $port
    Database = [Uri]::UnescapeDataString($matches['database'])
    User = [Uri]::UnescapeDataString($userinfo[0])
    Password = [Uri]::UnescapeDataString($userinfo[1])
  }
}

function Get-PostgresWindowsServices {
  return @(Get-Service -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match '^postgresql' -or $_.DisplayName -match 'PostgreSQL'
  })
}

function Invoke-UnaPsql {
  param(
    [Parameter(Mandatory=$true)]$Config,
    [Parameter(Mandatory=$true)][string]$Database,
    [string]$Query,
    [string]$File,
    [switch]$TuplesOnly
  )
  $psql = Find-PostgresTool -Name 'psql'
  if (-not $psql) { throw 'No se encontró psql. Instala PostgreSQL para Windows y sus herramientas de línea de comandos.' }
  $arguments = @('-X','-w','-v','ON_ERROR_STOP=1','-h',$Config.Host,'-p',[string]$Config.Port,'-U',$Config.User,'-d',$Database)
  if ($TuplesOnly) { $arguments += @('-t','-A') }
  if ($Query) { $arguments += @('-c',$Query) }
  if ($File) { $arguments += @('--single-transaction','-f',(Resolve-Path -LiteralPath $File).Path) }
  $oldPassword = $env:PGPASSWORD
  try {
    $env:PGPASSWORD = $Config.Password
    $output = & $psql @arguments
    if ($LASTEXITCODE -ne 0) { throw "psql no pudo completar la operación en '$Database'. Revisa credenciales, permisos y el servicio PostgreSQL." }
    return $output
  } finally {
    $env:PGPASSWORD = $oldPassword
  }
}

function ConvertTo-SqlLiteral {
  param([Parameter(Mandatory=$true)][string]$Value)
  return "'" + $Value.Replace("'","''") + "'"
}

function Get-UnaLanAddress {
  $candidate = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
    Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4DefaultGateway -and $_.IPv4Address } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Where-Object { $_ -and $_ -notlike '169.254.*' -and $_ -ne '127.0.0.1' } |
    Select-Object -First 1
  if ($candidate) { return $candidate }
  return [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
    Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and -not [System.Net.IPAddress]::IsLoopback($_) } |
    Select-Object -ExpandProperty IPAddressToString -First 1
}

function Test-UnaPort {
  param([string]$HostName='127.0.0.1',[int]$Port,[int]$TimeoutMilliseconds=750)
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $result = $client.BeginConnect($HostName,$Port,$null,$null)
    if (-not $result.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)) { return $false }
    $client.EndConnect($result)
    return $true
  } catch { return $false } finally { $client.Dispose() }
}
