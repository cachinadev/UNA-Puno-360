$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop es necesario para cargar la demostración.' }

docker compose exec api python -m app.community_cli seed-demo
docker compose exec api python -m app.facility_cli seed-demo
Get-Content services\api\examples\transport.demo.sql -Raw | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
foreach ($kind in 'branches','books','locations','menus','announcements') {
  docker compose exec api python -c "from app.import_services import import_csv; print(import_csv('$kind','examples/$kind.demo.csv'))"
}
Write-Host 'Datos de DEMOSTRACIÓN cargados; no representan información oficial.' -ForegroundColor Yellow
