# UNA Data Hub v0.2 — PostGIS / OpenStreetMap GeoAPI

Prototype; **not an official UNA Puno system**. Geographical information comes from OpenStreetMap and needs institutional verification before being identified as an official university resource. Uses © OpenStreetMap contributors, ODbL. The `demo` samples are explicitly fictional.

## Requirements
- Docker Engine + Docker Compose v2, or Docker Desktop on macOS/Windows.
- Docker image `postgis/postgis:17-3.7` currently supports `linux/amd64`; on Apple Silicon ARM it runs under emulation and can be slow. For production choose a vetted native ARM image or AMD64 host.
- Internet for images, CDN and for `import-osm` (the public Overpass service).

## Quick start
```bash
cp .env.example .env
# IMPORTANT: replace POSTGRES_PASSWORD in .env, and update the matching password inside DATABASE_URL
# Set a real contact email in OVERPASS_USER_AGENT before remote imports.
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

**Do not publish port 5432.** Docker Compose does not expose it. API port 8000 is localhost-only. The database is initialized at first boot using `sql/001_init.sql` (PostGIS extension and indexed tables). To reapply SQL later after an existing data volume, use `docker compose exec -T db psql -U una_user -d una_hub < sql/001_init.sql`.

## Demo without Overpass
```bash
docker compose exec api python -m app.cli seed-demo
curl 'http://127.0.0.1:8000/geo/geojson'
```
Demo markers are NOT actual UNA buildings or stops.

## Import real OpenStreetMap POIs in the pilot bounding box
```bash
docker compose exec api python -m app.cli import-osm
# or a smaller rectangle (South West North East)
docker compose exec api python -m app.cli import-osm --bbox -15.84 -70.03 -15.81 -70.00
```
Use sparingly; one-time manual import is the default. No automated bulk scraping. Uses fixed Overpass tag filters, limited bounding box, timeouts, and upserts; duplicate imports update existing places. A partial error does not delete previously synced data.

## Academic metadata import (operator-run)
```bash
docker compose exec api python -m app.cli sync-dspace --query quinua --size 5
docker compose exec api python -m app.cli sync-oai
curl "http://127.0.0.1:8000/records?q=quinua"
```
These are live network calls; servers can reject or rate-limit them. Use one page only, avoid bulk harvesting.

## API
- `GET /health` — database/PostGIS status
- `GET /sources` — provenance
- `GET /geo/categories` — available categories
- `GET /geo/places?category=library&limit=20`
- `GET /geo/places?south=-15.86&west=-70.05&north=-15.78&east=-69.98`
- `GET /geo/nearby?lat=-15.827&lon=-70.019&radius_m=1000`
- `GET /geo/geojson` — GeoJSON FeatureCollection (max 1,000 places)
- `GET /geo/places/1` — detail
- `GET /records?q=quinua` — public academic metadata saved by the DSpace/OAI import
- `GET /docs` — Swagger UI
- `GET /map` — read-only MapLibre demo with OpenStreetMap tiles, requires internet

Distances use PostGIS `geography` in **metres** (straight-line distances, not walking-route ETAs). GeoJSON coordinates use **[longitude, latitude]**. Result limits apply and `/geo/places` supports pagination.

## Local test suite without database
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

## Optional tests with running database
```bash
docker compose exec -e RUN_DB_TESTS=1 api python -m pytest -q
```

## Transition from v0.1
The previous SQLite DSpace/OAI-PMH prototype is retained under `legacy/hub_sqlite_v01.py` for reference. v0.2 includes equivalent one-page DSpace/OAI imports saved into Postgres and exposes `/records`, but **does not migrate existing SQLite rows automatically**. Sync to populate the new table.

## Deployment safeguards
- `POSTGRES_PASSWORD` is development configuration; replace it. Ensure `DATABASE_URL` uses the same credential.
- Restrict CORS, install HTTPS at reverse proxy, limit traffic, enable structured logs and backups, and add authentication before exposing admin functions.
- The public API is read-only; Overpass importer is CLI-only.
- Do not publish potentially personal student datasets.
- Respect OSM attribution and the ODbL share-alike rules for derivative databases. For production tile use, follow OpenStreetMap tile usage policy or use another tile provider/self-host.
- Avoid running `docker compose down -v` unless you intend to DELETE stored database contents.
- The map demo loads MapLibre from an external CDN; for production pin and self-host the JS/CSS assets.


## v0.3 — Biblioteca y Comedor (públicos; sin datos personales)

**Primer despliegue desde cero:** `docker compose up -d --build`. Docker ejecuta `001_init.sql` y `002_services.sql` solo al crear un volumen NUEVO.

**Actualización de v0.2 con una base de datos EXISTENTE:** antes de iniciar la nueva API, ejecutar `docker compose up -d db` y luego:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/002_services.sql
docker compose up -d --build api
```

### Carga de demostración (TODOS LOS DATOS SON FICTICIOS)

```bash
docker compose exec api python -m app.cli import-service branches examples/branches.demo.csv --dry-run
docker compose exec api python -m app.cli import-service branches examples/branches.demo.csv
docker compose exec api python -m app.cli import-service books examples/books.demo.csv
docker compose exec api python -m app.cli import-service locations examples/locations.demo.csv
docker compose exec api python -m app.cli import-service menus examples/menus.demo.csv
docker compose exec api python -m app.cli import-service announcements examples/announcements.demo.csv
```

Endpoints de lectura: `/library/info`, `/library/branches`, `/library/books?q=energia`, `/library/books/{external_id}`, `/dining/info`, `/dining/locations`, `/dining/menus?day=2026-11-10`, `/dining/announcements`. Swagger: `/docs`.

Las importaciones requieren un CSV **verificado manualmente**; no se realiza scraping de cuentas privadas ni se leen padrones, expedientes socioeconómicos o datos de préstamos. Las páginas oficiales son `https://biblioteca.unap.edu.pe/opac_css/` y `https://comedor.unap.edu.pe/`.

La disponibilidad de ejemplares no está conectada a una API pública confirmada del catálogo PMB. Solo debe publicarse como `available`/`unavailable` con una fuente fiable, permiso institucional y `verified=true`. Convocatorias, menús, horarios y demás datos no deben tratarse como información oficial si `verified=false`.
