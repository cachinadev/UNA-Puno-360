# UNA Puno 360 — Tu universidad en tus manos

MVP integrado para estudiantes de la Universidad Nacional del Altiplano, construido a partir de los prototipos UNA Data Hub disponibles en este repositorio. Es un proyecto independiente: **no constituye un servicio oficial de la UNA** y no afirma que los datos de demostración hayan sido verificados por la institución.

## Incluye

- Web responsive Next.js con panel estudiantil y ruta administrativa.
- Aplicación móvil Expo/React Native preparada para Android e iOS.
- API FastAPI con autenticación local, sesiones revocables, comunidad, biblioteca, comedor, transporte, mapa, servicios cercanos y moderación.
- PostgreSQL/PostGIS, migraciones SQL, datos demo claramente identificados y Docker Compose.
- Cliente API y tipos TypeScript compartidos.
- Scripts PowerShell de preparación, ejecución, pruebas, semillas y salud.

## Inicio rápido nativo en Windows

Requisitos: Windows 10/11, PostgreSQL/PostGIS local, Node.js 20+, Python 3.10+ y PowerShell. Docker no es necesario.

```powershell
Set-Location 'C:\Users\Usuario\Documents\Github\UNA Puno 360'
.\scripts\setup-native.ps1
.\scripts\dev-native.ps1
.\scripts\health-check.ps1
.\scripts\seed-native.ps1
```

Accesos locales:

- Web: http://localhost:3000
- Administración: http://localhost:3000/admin
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

La guía completa, incluyendo PostgreSQL/PostGIS y Expo, está en [Desarrollo nativo en Windows](docs/WINDOWS_NATIVE_SETUP.md). Docker Compose permanece disponible como alternativa opcional.

## Primer superadministrador

El primer superadministrador solo se crea desde una terminal confiable, nunca por registro público:

```powershell
Set-Location services\api
.\.venv\Scripts\python.exe -m app.accounts_cli bootstrap-admin admin@example.edu.pe "Administrador inicial"
```

La contraseña se solicita sin eco. El comando queda deshabilitado cuando ya existe un administrador o superadministrador.

## Desarrollo sin Docker para frontend

```powershell
corepack prepare pnpm@9.15.4 --activate
corepack pnpm install
corepack pnpm --filter @una/web dev
corepack pnpm --filter @una/mobile start
```

En un teléfono físico, configure `EXPO_PUBLIC_API_URL` con la IP LAN del host Windows; `localhost` apunta al teléfono, no al equipo de desarrollo.

## Pruebas

```powershell
.\scripts\test-native.ps1
```

Las pruebas unitarias de backend no necesitan Postgres. La prueba de integración se omite cuando `DATABASE_URL` no está configurada; ejecútela contra el Compose levantado para validar PostGIS. El script también ejecuta TypeScript y el build web cuando pnpm está instalado.

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Base de datos](docs/DATABASE.md)
- [API](docs/API.md)
- [Despliegue en Windows](docs/DEPLOYMENT_WINDOWS.md)
- [Desarrollo nativo en Windows](docs/WINDOWS_NATIVE_SETUP.md)
- [Seguridad](docs/SECURITY.md)
- [Integración de fuentes](docs/SOURCE_INTEGRATION_REPORT.md)
- [Limitaciones conocidas](docs/KNOWN_LIMITATIONS.md)
- [Resultados de validación](docs/TEST_RESULTS.md)
