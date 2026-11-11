# Desarrollo nativo en Windows (sin Docker)

Este flujo ejecuta PostgreSQL/PostGIS, FastAPI, Next.js y Expo directamente en Windows. Docker Compose se conserva como alternativa para producción Linux y no es un requisito de desarrollo.

## 1. Requisitos

- Windows 10/11 y PowerShell 5.1 o PowerShell 7.
- Python 3.10 o superior, disponible como `python`.
- Node.js 20 o superior con Corepack.
- PostgreSQL 16, 17 o 18 para Windows, incluyendo Command Line Tools.
- PostGIS correspondiente exactamente a la versión principal de PostgreSQL, instalado mediante StackBuilder o el instalador oficial.
- Android Studio para un emulador Android; alternativamente un teléfono y una versión de Expo Go compatible con el SDK del proyecto.

Durante la instalación de PostgreSQL, conserve la contraseña local en un gestor seguro. Los scripts no la generan, imprimen ni escriben en argumentos de proceso.

Compruebe la instalación:

```powershell
python --version
node --version
corepack --version
Get-Service *postgres*
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --version
```

Si desea una cuenta separada de desarrollo, conéctese como el administrador creado por el instalador:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres
```

Dentro de `psql`, use una contraseña ingresada de forma interactiva:

```sql
CREATE ROLE una_user LOGIN CREATEDB;
\password una_user
\q
```

El privilegio `CREATEDB` solo se necesita para que el script cree `una_puno_360`. Puede pedir al administrador que cree la base y retirar ese privilegio después.

## 2. Entorno local

Desde el repositorio:

```powershell
Set-Location 'C:\Users\Usuario\Documents\Github\UNA Puno 360'
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
```

Configure `DATABASE_URL` con el usuario y contraseña reales. Codifique caracteres especiales de usuario/contraseña como URL. Para desarrollo nativo el host debe ser `127.0.0.1`, no `db`.

Valores principales:

```dotenv
DATABASE_URL=postgresql://una_user:CLAVE_CODIFICADA@127.0.0.1:5432/una_puno_360
API_HOST=127.0.0.1
API_PORT=8000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_MAP_TILE_URL=https://tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_MAP_ATTRIBUTION=© OpenStreetMap contributors
```

No confirme `.env` en Git. `setup-native.ps1` genera secretos aleatorios locales cuando encuentra placeholders, sin mostrarlos en consola.

## 3. Preparación

```powershell
.\scripts\setup-native.ps1
```

Este comando:

- crea `services/api/.venv`;
- instala FastAPI y sus dependencias;
- instala el workspace pnpm;
- detecta `psql` incluso si no está en `PATH`;
- inicia el servicio PostgreSQL cuando tiene permisos;
- crea la base solamente si no existe;
- comprueba que PostGIS esté disponible;
- aplica `services/api/sql/*.sql` en orden y registra checksums en `una_schema_migrations` (actualmente 001–008).

No elimina tablas, bases ni datos. Si una migración aplicada cambió, se detiene para evitar una reaplicación insegura.

Para preparar Python/Node antes de instalar PostgreSQL:

```powershell
.\scripts\setup-native.ps1 -SkipDatabase
```

## 4. Inicio diario

El comando principal es:

```powershell
.\scripts\dev-native.ps1
```

Abre FastAPI y Next.js en ventanas de PowerShell separadas y deja sus logs visibles.

- Web: http://localhost:3000
- Administración: http://localhost:3000/admin
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Compruebe el sistema:

```powershell
.\scripts\health-check.ps1
```

## 5. Base de datos y demostración

Puede ejecutar la preparación de base por separado:

```powershell
.\scripts\db-native.ps1 -StartService
.\scripts\seed-native.ps1
```

Las semillas son idempotentes cuando el esquema lo permite y se identifican como demostración. No representan ubicaciones, catálogos, menús ni GPS oficiales.

Para crear el primer superadministrador:

```powershell
Set-Location services\api
.\.venv\Scripts\python.exe -m app.accounts_cli bootstrap-admin admin@example.edu.pe 'Administrador inicial'
Set-Location ..\..
```

## 6. Expo y Android

Emulador Android:

```powershell
.\scripts\dev-native.ps1 -Mobile -AndroidEmulator
```

El emulador usa `http://10.0.2.2:8000` para llegar al host Windows.

Dispositivo físico en la misma red privada:

```powershell
.\scripts\dev-native.ps1 -Mobile -PhysicalDevice
```

El script detecta la IPv4 LAN, configura `EXPO_PUBLIC_API_URL` y levanta FastAPI en `0.0.0.0`. No modifica el Firewall de Windows. Si Windows solicita acceso, autorice Python únicamente para redes privadas después de revisar la solicitud. Nunca use `localhost` en el teléfono: apuntaría al propio teléfono.

Expo Go solo funciona si la versión instalada admite el SDK Expo del repositorio. Si no, use un development build compatible.

## 7. Pruebas

```powershell
.\scripts\test-native.ps1
```

Ejecuta pytest, la integración PostGIS cuando la base está disponible, typecheck, build Next.js, pruebas web, bundle Android y Playwright. Para omitir componentes opcionales:

```powershell
.\scripts\test-native.ps1 -SkipE2E -SkipMobile
```

Con API y base ya iniciadas, ejecute el recorrido real de registro, verificación, login, comunidad, eventos, reportes, transporte, mapa, servicios, permisos admin y logout:

```powershell
.\scripts\test-native.ps1 -LiveApi
```

Este recorrido crea cuentas y contenido claramente marcados como pruebas nativas.

## 8. Diagnóstico

```powershell
Get-Service *postgres* | Format-Table Name,Status,StartType
.\scripts\db-native.ps1 -CheckOnly
Get-NetTCPConnection -LocalPort 3000,8000,5432 -ErrorAction SilentlyContinue
Invoke-RestMethod http://127.0.0.1:8000/health
```

Problemas frecuentes:

- `psql no encontrado`: instale Command Line Tools o agregue `C:\Program Files\PostgreSQL\<versión>\bin` a PATH. El script también busca esa ubicación automáticamente.
- servicio detenido: abra PowerShell como administrador una vez o inícielo desde `services.msc`.
- autenticación fallida: revise `DATABASE_URL` y `pg_hba.conf`; la contraseña no debe quedar sin codificar si contiene `@`, `:`, `/` o `%`.
- rol o contraseña rechazados tras instalar PostgreSQL: ejecute `.\scripts\db-native.ps1 -StartService -RepairRole`. El script pide de forma oculta la contraseña del superusuario `postgres`, crea o repara únicamente el rol/base configurados en `.env` y habilita PostGIS. La contraseña no aparece en argumentos ni en consola.
- PostGIS no disponible: ejecute StackBuilder para la misma versión de PostgreSQL.
- `CREATE EXTENSION` denegado: habilite PostGIS como administrador de la base y vuelva a ejecutar el script.
- puerto ocupado: cierre el proceso anterior o cambie `API_PORT`/`WEB_PORT` en `.env`.

## Docker opcional

`compose.yaml` y los Dockerfiles siguen disponibles. Compose construye su URL interna con el host `db`, aunque `.env` use `127.0.0.1`, por lo que ambos flujos pueden convivir.
