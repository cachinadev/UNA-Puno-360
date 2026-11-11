# Informe de integración de fuentes

Se inspeccionaron los directorios extraídos y los siete ZIP conservados bajo `-/`. Los originales no se sobrescribieron ni eliminaron. v07 es acumulativo y fue copiado a `services/api` como base verificable; las mejoras se aplicaron únicamente sobre la copia consolidada.

| Fuente | Evidencia reutilizada | Decisión |
|---|---|---|
| Starter v01 ZIP / legado SQLite | `hub.py`, conector académico heredado | Conservado como evidencia; reemplazado por PostgreSQL/PostGIS |
| v02 | `academic.py`, `geo.py`, `osm.py`, `001_init.sql`, mapa | Reutilizado a través de la línea acumulativa v07 |
| v03 | `services.py`, importador CSV, `002_services.sql`, ejemplos | Reutilizado; mantiene disponibilidad no verificada por defecto |
| v04 | comunidad, grupos, posts, eventos, reportes, `003_community.sql` | Reutilizado y autorizado por identidad única |
| v05 | cuentas, administración, Argon2/JWT, `004_accounts.sql` | Modificado: superadmin inicial, CORS, cabeceras y rate limit |
| v06 | transporte, puente, webhook, `005_transport.sql`, demo | Reutilizado; KUNTUR/Rutas quedan como integraciones no autorizadas |
| v07 | instalaciones, OSM, revisión, `006_services_finder.sql` | Base acumulativa consolidada; roles ampliados con controles equivalentes |

## Conflictos resueltos

- Se eligió una sola estrategia de conexión (`app.db.connection`) y una sola identidad (`community_users`).
- Las migraciones se ejecutan una vez y en orden desde el Compose raíz.
- La autenticación de desarrollo de v04 no reemplaza las sesiones revocables de v05.
- Los permisos administrativos se validan en FastAPI, no por visibilidad de navegación.
- Los datos demo de transporte e instalaciones conservan etiquetas explícitas y no se afirman como oficiales.
- La web HTML heredada se conserva en la API para compatibilidad; la experiencia principal ahora vive en Next.js.

## No disponible o pendiente

No se encontró código Next.js, Expo, shadcn/ui, Playwright, proveedor real de correo, contrato OIDC institucional ni credenciales documentadas de KUNTUR/Rutas. Se crearon los clientes web/móvil y pruebas Playwright de la interfaz; las conexiones externas requieren autorización y pruebas del operador.
