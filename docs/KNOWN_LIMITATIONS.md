# Limitaciones conocidas

- No existe autorización ni contrato documentado para SSO institucional, KUNTUR, Rutas CACHINA, PMB, menús oficiales o datos oficiales UNA. Las posiciones y rutas visibles están marcadas como demostrativas y no son GPS real.
- El proveedor de teselas web se configura con `NEXT_PUBLIC_MAP_TILE_URL` y `NEXT_PUBLIC_MAP_ATTRIBUTION`. El valor de desarrollo usa infraestructura pública con atribución; producción debe contratar o alojar un servicio con capacidad y política adecuadas. El modo totalmente offline todavía requiere teselas propias.
- La administración web ya opera moderación y reservas reales, pero aún no incluye editores completos para libros, menús, eventos, usuarios, rutas ni una consola global persistente del reloj de simulación. Los controles de transporte actuales son funcionales y locales a la sesión del navegador.
- Las rutas `/comunidad/post/[id]`, `/comunidad/grupos`, `/comunidad/grupos/[id]` y `/comunidad/mis-publicaciones` existen, pero por ahora redirigen al feed integrado; no tienen vistas de detalle separadas.
- La UI permite crear publicaciones de texto. El backend acepta una URL de imagen validada, pero no existe almacenamiento/carga binaria de imágenes ni procesamiento antivirus.
- El limitador de credenciales es por proceso. Un despliegue con varios workers debe usar Redis o un gateway compartido.
- Expo Android compila y conserva el dashboard/servicios básicos, pero no replica todavía toda la experiencia MapLibre, comunidad, reservas y administración de la web. iOS requiere EAS Build o macOS.
- Inglés, quechua y aimara son opciones de preferencia pendientes de traducción revisada; la copia visible permanece en español.
- Las pruebas de navegador crean cuentas de desarrollo y contenido temporal claramente identificable. Las publicaciones principales se eliminan al terminar, pero las cuentas de prueba permanecen para trazabilidad local.
- La advertencia de deprecación de `fastapi.testclient`/Starlette no afecta el resultado actual, pero conviene migrar a la versión recomendada por FastAPI cuando se actualicen dependencias.
