# Integraciones externas

- `kuntur`: telemetría prevista mediante webhook HMAC o puente con token; no se presuponen endpoints privados.
- `rutas`: posible catálogo/geometría; requiere contrato documentado.
- `osm`: importación limitada mediante Overpass y revisión humana previa a publicación.
- `dspace` / `oai-pmh`: conectores académicos heredados; la disponibilidad real depende del servicio remoto.
- `sso`: adaptador OAuth 2.0 / OpenID Connect pendiente de autorización institucional.

Los secretos pertenecen únicamente al backend y nunca se exponen a web o móvil.
