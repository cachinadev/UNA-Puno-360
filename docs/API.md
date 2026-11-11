# API REST

Swagger está disponible en `/docs` y OpenAPI en `/openapi.json`.

| Prefijo | Función | Acceso |
|---|---|---|
| `/auth` | registro, verificación, login, refresh, logout, contraseña | público o sesión |
| `/admin` | cuentas, roles, suspensiones, reportes, auditoría, resumen | admin/moderador según ruta |
| `/community` | grupos, feed, posts, comentarios, reacciones, eventos | sesión; lectura pública limitada |
| `/library`, `/dining` | catálogos, sedes, menús, anuncios | lectura pública |
| `/geo` | lugares, GeoJSON, cercanía | lectura pública |
| `/facilities` | categorías, búsqueda, mapa y revisión | lectura pública / administración |
| `/transport` | rutas, paradas, vehículos e ingesta firmada | lectura pública / integración privada |
| `/records` | repositorio académico normalizado | lectura pública |

## Autenticación local de desarrollo

El registro nunca acepta un rol. Tras registrar, el correo queda pendiente; cuando `APP_ENV=development` y `AUTH_DEV_EXPOSE_TOKENS=true`, la respuesta entrega un token explícitamente de desarrollo. En producción debe existir entrega por correo verificada y `AUTH_DEV_EXPOSE_TOKENS=false`.

Los access tokens expiran en 15 minutos. Refresh rota en cada uso y logout revoca la sesión. Los endpoints `/auth/*` tienen un límite local de 10 solicitudes por minuto por IP y ruta; producción con varios workers debe usar Redis o gateway.

## Webhook de transporte

`POST /transport/internal/webhook` exige `X-Transport-Timestamp` dentro de cinco minutos y `X-Transport-Signature: sha256=<HMAC>`, calculado sobre `<timestamp>.<cuerpo exacto>`. Solo vehículos previamente aprovisionados se aceptan. Las observaciones duplicadas o fuera de orden no sustituyen una posición más nueva.
