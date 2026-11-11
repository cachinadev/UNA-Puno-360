# Arquitectura

UNA Puno 360 es un monorepo pnpm con tres límites principales:

1. `apps/web`: Next.js App Router sirve la experiencia estudiantil y `/admin`.
2. `apps/mobile`: Expo Router consume la misma API y guarda futuros tokens en SecureStore.
3. `services/api`: FastAPI concentra reglas, autorización, adaptadores y persistencia PostGIS.

`packages/api-client`, `packages/shared-types` y `packages/design-tokens` evitan duplicar contratos entre clientes. El navegador y la app móvil nunca reciben credenciales de base de datos ni secretos de proveedores.

## Flujo de datos

Los clientes llaman REST a FastAPI. Las rutas públicas leen únicamente registros publicables. Las escrituras administrativas validan JWT y rol en backend, registran auditoría y mantienen los registros nuevos ocultos hasta revisión. PostgreSQL almacena estado transaccional y PostGIS resuelve búsquedas espaciales. Redis está reservado para un limitador distribuido y caché cuando se escale a varios workers; el MVP local usa un limitador de autenticación por proceso.

## Identidad

La identidad única vive en `community_users`. Las cuentas locales son un mecanismo piloto deshabilitable; las sesiones tienen refresh token hasheado, expiración y revocación. El primer `superadmin` se crea fuera de banda. Un adaptador OIDC institucional es trabajo futuro y no se simula como autorizado.

## Geodatos y transporte

OSM/Overpass es fuente importable, nunca fuente oficial automática: un moderador revisa antes de publicar. El transporte admite webhook HMAC y puente con token para proveedores aprovisionados. La API pública nunca expone IMEI, credenciales, SOS o vídeo. Estados de telemetría deben distinguir `live`, `stale`, `offline` y `demonstration`.

## Internacionalización

El texto actual está en español. La estructura admite catálogos futuros para `es`, `en`, `qu` y `ay`; no se incluyen traducciones no revisadas.
