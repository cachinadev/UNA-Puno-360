# Despliegue local en Windows

## Requisitos

- Docker Desktop funcionando con contenedores Linux y WSL2.
- Node.js 20 o superior con Corepack.
- Python 3.10 o superior para pruebas fuera del contenedor.
- PowerShell 5.1 o superior.

## Instalación

```powershell
Set-Location 'C:\Users\Usuario\Documents\Github\UNA Puno 360'
.\scripts\setup.ps1
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
docker compose config
docker compose up --build -d
docker compose ps
.\scripts\health-check.ps1
```

Genere secretos largos y aleatorios; no conserve los valores `replace_`. Para detener sin borrar datos:

```powershell
docker compose stop
```

## Dispositivo móvil

Obtenga la IP LAN con `Get-NetIPAddress -AddressFamily IPv4`. En `apps/mobile/.env`, use por ejemplo `EXPO_PUBLIC_API_URL=http://192.168.1.20:8000`. Compose enlaza la API a loopback por seguridad; para probar desde un teléfono deberá cambiar conscientemente el binding de `api.ports` a `0.0.0.0`, confirmar que la red es confiable y configurar el firewall manualmente. Los scripts no modifican el firewall.

## Diagnóstico

```powershell
docker compose logs api --tail 100
docker compose logs db --tail 100
docker compose exec db pg_isready -U una_user -d una_puno_360
Invoke-RestMethod http://localhost:8000/health
```

Si el volumen ya existía antes de una nueva migración, el init de Postgres no la repetirá. Respalde y aplique el SQL pendiente manualmente.
