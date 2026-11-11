# Progreso del MVP interactivo

Fecha de corte: 2026-11-11.

## Entregado y verificado

- Flujo nativo de Windows sin Docker: detección de PostgreSQL 18, servicio, credenciales, PostGIS 3.7, migraciones, semillas y lanzadores separados para FastAPI, Next.js y Expo.
- Mapa MapLibre reutilizable con altura explícita, carga/error/reintento, comprobación de WebGL, `ResizeObserver`, navegación, atribución y proveedor de teselas configurable.
- Transporte demostrativo con tres circuitos, cuatro vehículos, rutas, doce paraderos, ETA, ocupación, dirección, estados, seguimiento, selección de paradero/vehículo y controles 1x/2x/5x, pausa y reinicio.
- Catálogo sintético de 60 libros y reservas transaccionales persistentes; menús demostrativos con cuota; 24 eventos con capacidad, inscripción y cancelación.
- Agenda pública para invitados. Las acciones de inscripción siguen protegidas.
- UNA Comunidad persistente: ocho grupos ficticios, publicaciones, edición/eliminación del autor, comentarios, reacciones, marcadores, reportes y notificaciones.
- Separación visible de invitado, estudiante y personal autorizado. El menú administrativo no aparece para estudiantes y la API devuelve 403 ante acceso directo.
- Panel administrativo protegido con métricas, moderación y gestión operativa de reservas de biblioteca/comedor según rol.
- Perfil, preferencias, notificaciones, cierre de sesión y tema persistentes.
- Bundle Android Expo y contratos de API compartidos validados.

## Corrección del mapa en blanco

La causa visual fue una combinación de tres fallos reales:

1. `maplibre-gl.css` se importaba después de `globals.css`; su regla `.maplibregl-map { position: relative }` anulaba el posicionamiento absoluto del contenedor y lo dejaba con altura calculada de 0 px.
2. El navegador abría `127.0.0.1:3000`, pero la API/CORS y el bundle apuntaban a `localhost`, por lo que las solicitudes de datos se bloqueaban.
3. La primera instantánea podía llegar antes del evento `load` del mapa y las fuentes GeoJSON no se volvían a actualizar.

Se corrigieron el orden de CSS, la configuración de host/CORS, las dimensiones y el ciclo de preparación de fuentes. La aceptación automatizada genera `apps/web/artifacts/playwright/transport-acceptance.png`.

## Esquema y datos

- Migraciones 001–008 aplicadas sin borrar datos.
- La migración 008 amplía roles y añade categoría/imagen/clave demo de publicaciones, respuestas de comentarios y marcadores.
- `seed-native.ps1` es idempotente y mantiene separados los registros demostrativos.

## Ejecución

```powershell
.\scripts\dev-native.ps1
.\scripts\health-check.ps1
.\scripts\test-native.ps1 -LiveApi
```

Las limitaciones restantes están registradas en `docs/KNOWN_LIMITATIONS.md`; no se presentan como completas las integraciones institucionales ni el GPS real.
