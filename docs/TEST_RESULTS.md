# Resultados de validación

Fecha: 2026-11-11. Entorno: Windows nativo, PostgreSQL 18.6, PostGIS 3.7, Python 3.10, Node.js 20 y pnpm mediante Corepack. Docker no fue necesario.

| Verificación | Resultado | Evidencia |
|---|---|---|
| Servicio y conexión PostgreSQL | PASS | `postgresql-x64-18` activo; conexión a `una_puno_360` |
| PostGIS | PASS | `3.7 USE_GEOS=1 USE_PROJ=1 USE_STATS=1` |
| Migraciones | PASS | 001–008 registradas; segunda ejecución no reaplica cambios |
| Semilla | PASS | 3 rutas, 4 buses, 60 libros, 21 menús, 24 eventos y 8 grupos |
| Pytest con DB (`test-native.ps1`) | PASS | 50 aprobadas, 1 aviso de deprecación |
| TypeScript monorepo | PASS | design tokens, shared types, API client, web y mobile |
| Next.js producción | PASS | compilación y generación de 17 rutas |
| Vitest | PASS | no hay archivos de componente; salida limpia con `--passWithNoTests` |
| Expo Android | PASS | 901 módulos y bundle Hermes de 2.48 MB |
| Playwright Chromium | PASS | 8 de 8 |
| Recorrido API real | PASS | auth, perfil, comunidad, eventos, reportes, transporte, geo, biblioteca, comedor, avisos, instalaciones, permisos y logout |
| `scripts/test.ps1` obligatorio | PASS | 49 aprobadas y 1 integración DB omitida por diseño de ese runner; typecheck y build aprobados |

## Validación visual del transporte

La prueba `e2e/transport-visual.spec.ts` no se limita a HTTP 200. Comprueba:

- estado `ready` de MapLibre y lienzo WebGL con ancho/alto mayores que cero;
- al menos una tesela del mapa base cargada y ninguna solicitud de tesela fallida;
- tres rutas cargadas, tres selectores y cuatro marcadores;
- desplazamiento medible del bus `DEMO-BUS-1`;
- estabilidad de posición al pausar, reanudación, velocidad 5x y cambio de circuito;
- ausencia de errores de consola;
- captura `apps/web/artifacts/playwright/transport-acceptance.png`.

## Autenticación y comunidad

`e2e/auth-community.spec.ts` crea cuentas de desarrollo verificadas y comprueba agenda pública, bloqueo de comunidad/admin para invitados, publicación persistente tras recarga, comentario y reacción desde otra cuenta, edición/eliminación por el autor, 403 al editar contenido ajeno, 403 de estudiante contra `/admin/overview` y ausencia del enlace administrativo.

La primera ejecución completa detectó una tolerancia visual demasiado estricta (0.25 px) para movimiento subpíxel en producción. Se amplió la observación a 4 segundos y se mantuvo una exigencia positiva de movimiento; la repetición completa terminó 8/8.

## Comandos finales

```powershell
.\scripts\test-native.ps1 -LiveApi
.\scripts\test.ps1
.\scripts\health-check.ps1
```
