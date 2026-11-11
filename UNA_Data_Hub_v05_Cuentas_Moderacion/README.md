# UNA Data Hub v0.5 — Cuentas, inicio de sesión y moderación

Módulo **offline / piloto** ensamblado sobre v0.4. Incluye las APIs anteriores: GeoData, DSpace, biblioteca, comedor y comunidad. **No es un sistema oficial de la UNA Puno ni verifica matrícula universitaria.**

## Funcionalidades

- Registro con correo y contraseña, Argon2id, verificación mediante token de un solo uso.
- Login JWT de acceso (15 minutos) y refresh rotativo (7 días), logout, expiración y revocación de sesiones.
- Cambio y restablecimiento de contraseña, bloqueo de usuario tras 5 intentos fallidos (15 min).
- Roles `student`, `moderator`, `admin` aplicados en el backend.
- Administración de usuarios, suspensión, bloqueo definitivo, asignación de rol moderador, revocación de sesiones y auditoría.
- Cola de denuncias y acciones de moderación (ocultar / desestimar) con registro en `admin_audit`.
- **Sin envío de correo**: para pruebas offline, tokens de verificación/reset se generan en consola o se muestran **solo** si `APP_ENV=development` y `AUTH_DEV_EXPOSE_TOKENS=true`.

## Instalación nueva

```bash
cp .env.example .env
# Edite .env con nueva contraseña y nuevos secretos
# genere dos secretos INDEPENDIENTES con: openssl rand -hex 48
# ajuste POSTGRES_PASSWORD, DATABASE_URL, AUTH_JWT_SECRET y COMMUNITY_JWT_SECRET
# AUTH_LOCAL_ENABLED=true y AUTH_ALLOW_REGISTRATION=true solo en entorno de prueba

docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
# Swagger: http://127.0.0.1:8000/docs
```

La instalación nueva ejecuta las migraciones 001–004 automáticamente solo cuando se crea un volumen vacío.

## Migración desde v0.4, sin perder datos

1. **Respalde** PostgreSQL y compruebe que puede restaurarlo.
2. Mantenga el nombre del proyecto Docker/volumen anterior: de lo contrario se crea otro volumen.
3. Aplique las migraciones a la base anterior **solo una vez**, desde una carpeta que contenga el archivo SQL.

```bash
# EJEMPLO: desde carpeta v0.5, si la BD ya está arrancada con datos antiguos
# Use -p <nombre-proyecto-anterior> si cambió el nombre de la carpeta.
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/004_accounts.sql

docker compose up -d --build api
```

Las cuentas ficticias v0.4 no reciben contraseña; deben crearse cuentas reales nuevas. Los tokens dev antiguos **no funcionan** con la autenticación v0.5.

## Cuenta de administración inicial (solo consola local)

```bash
docker compose exec -it api python -m app.accounts_cli bootstrap-admin admin@example.org "Administrador Piloto"
```

Pedirá una contraseña en consola y solo permite ejecutarse si no existe ningún administrador. No se permite elevar privilegios a admin mediante la API.

## Registro y verificación

Con `.env` local, `AUTH_DEV_EXPOSE_TOKENS=true` devuelve el token de verificación en el JSON de registro (**nunca en producción**).

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
 -H 'Content-Type: application/json' \
 -d '{"email":"estudiante@example.org","display_name":"Estudiante de prueba","password":"ClaveDePrueba12345","faculty":"Ingeniería Electrónica"}'
```

Si el modo dev no muestra el token, se obtiene desde consola:

```bash
docker compose exec -T api python -m app.accounts_cli verify-token estudiante@example.org
```

```bash
curl -X POST http://127.0.0.1:8000/auth/verify-email \
 -H 'Content-Type: application/json' \
 -d '{"token":"PEGAR_TOKEN"}'
```

## Login, usuario y logout

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
 -H 'Content-Type: application/json' \
 -d '{"email":"estudiante@example.org","password":"ClaveDePrueba12345"}'
# Copie access_token
curl -H 'Authorization: Bearer ACCESS_TOKEN' http://127.0.0.1:8000/auth/me
curl -H 'Authorization: Bearer ACCESS_TOKEN' http://127.0.0.1:8000/community/feed
curl -X POST -H 'Authorization: Bearer ACCESS_TOKEN' http://127.0.0.1:8000/auth/logout
```

`POST /auth/refresh` recibe `{ "refresh_token":"..." }` y devuelve un nuevo access token y un refresh token **rotado**.

`POST /auth/password/request-reset` solicita un enlace/token (el **envío de correos no está implementado**). Para generar token de reset por consola:

```bash
docker compose exec -T api python -m app.accounts_cli reset-token estudiante@example.org
```

Luego llamar `POST /auth/password/confirm-reset` con `{"token":"...","new_password":"OtraClaveSegura123"}`.

## Administración / Moderación

Autorización por Bearer JWT con rol correcto:

| Método | Ruta | Rol |
|---|---|---|
| GET | `/admin/users` | admin |
| PATCH | `/admin/users/{id}/status` | admin |
| PATCH | `/admin/users/{id}/role` | admin |
| GET | `/admin/reports` | moderator/admin |
| POST | `/admin/reports/{id}/resolve` | moderator/admin |
| GET | `/admin/audit` | admin |
| POST | `/community/reports` | estudiante autenticado |

Ejemplo suspender cuenta (desconecta sus sesiones):

```bash
curl -X PATCH http://127.0.0.1:8000/admin/users/USER_ID/status \
 -H 'Authorization: Bearer TOKEN_ADMIN' -H 'Content-Type: application/json' \
 -d '{"status":"suspended","reason":"Conducta inapropiada confirmada por revisión"}'
```

Ejemplo resolver denuncia:

```bash
curl -X POST http://127.0.0.1:8000/admin/reports/REPORT_ID/resolve \
 -H 'Authorization: Bearer TOKEN_MODERADOR' -H 'Content-Type: application/json' \
 -d '{"action":"hide","note":"Incumplimiento verificado de normas comunitarias"}'
```

## Pruebas

```bash
pytest -q
# Test de integración PostgreSQL (requiere Docker y base inicializada):
docker compose exec -e RUN_DB_TESTS=1 api python -m pytest -q
```

## Antes de uso con estudiantes reales

- Integrar **OIDC institucional / SSO**; una cuenta local no acredita pertenecer a la UNA.
- Implementar entrega de correos de verificación y recuperación por proveedor aprobado.
- Incorporar throttling global por IP y dispositivo en reverse proxy/API Gateway, captcha adaptativo y monitorización de intentos.
- Activar HTTPS, protección CSRF si se usan cookies, validación de origen y almacenamiento seguro de tokens en la app.
- Revisar permisos detallados de grupos privados y ejecutar pruebas de seguridad con autorización.
- Añadir MFA para administradores, gestión de incidentes, política de privacidad, retención, apelaciones y consentimiento conforme a ley peruana.
- Revisar riesgos de ataques de reutilización de refresh tokens; este piloto rota tokens, pero no implementa detección de reutilización a nivel de familia de tokens.
- Antes de desplegar, cambiar `APP_ENV=production`, `AUTH_DEV_EXPOSE_TOKENS=false` y desactivar el registro público hasta tener controles institucionales.

**Estado de verificación:** suite local sin PostgreSQL completada; pruebas contra Docker/PostgreSQL y flujo real de registro + login deben ejecutarse desde el entorno de despliegue.
