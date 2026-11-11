# UNA Data Hub v0.7 — Campus Services Finder

Standalone complete project based on UNA Data Hub v0.6. Integrates **PostgreSQL/PostGIS**, FastAPI, OSM/Overpass operator importer, a public GeoJSON API, a map/list UI, and a manual approval workflow. Retains academic records, community, accounts, dining, library and transport modules.

**Status:** prototype. The default public dataset is empty; all OSM imports remain hidden until an authorized moderator verifies them. No actual UNA campus facilities or medical practitioners have been independently validated. Coordinates in seed-demo are entirely fictitious. The example map downloads MapLibre JS/CSS and demo tiles when online: the backend/API and data tests can run offline, but an offline basemap requires self-hosted assets and tiles. Do not deploy as an official university service without authorization.

## Install (new environment)

```bash
unzip UNA_Data_Hub_v07_Campus_Services.zip
cd UNA_Data_Hub_v07_Services_Finder
cp .env.example .env
# Update postgres password, DATABASE_URL, JWT secrets, and OVERPASS_USER_AGENT contact.
docker compose up -d --build
curl http://127.0.0.1:8000/facilities/categories
```

Local UI: http://127.0.0.1:8000/services-map  
Swagger: http://127.0.0.1:8000/docs

**Existing v0.6 installation:** back up the database first and preserve the existing Compose `pgdata` volume (Compose project names are important). Apply `sql/006_services_finder.sql` to the existing database. Do **not** use `docker compose down -v`.

```bash
# From the copied v0.7 project attached to the existing DB volume:
docker compose up -d db
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/006_services_finder.sql
docker compose up -d --build api
```

For a fresh install, Compose initializes all six SQL files in numbered order. Container image builds and CDN-based map display require network access unless their dependencies were pre-cached. For fully offline building, pre-download the Python wheels and Docker images from a trusted environment.

## Import OpenStreetMap points for a pilot region

**Do not expose this CLI on a public endpoint**; only an operator calls Overpass and imports points. Choose a small bounded area in the actual region. Example bbox values are illustrative, not an official campus boundary.

```bash
docker compose exec api python -m app.facility_cli import-osm \
  --bbox -15.84 -70.03 -15.81 -70.00
```

Available categories: `food`, `cafe`, `printing`, `copies`, `bathroom`, `medical`, `medical_tests`, `pharmacy`, `water`, `wifi`, `atm`, `other`. Some categories (especially `copies`, Wi-Fi and clinical tests) usually need manual registration and verification; OSM tags may be incomplete. For repeated imports, unchanged rows keep their review status; changed source data is hidden until re-reviewed.

**Offline mock data (never visible in public API):**

```bash
docker compose exec api python -m app.facility_cli seed-demo
```

## Search examples

```bash
curl 'http://127.0.0.1:8000/facilities/categories'
curl 'http://127.0.0.1:8000/facilities/search?category=printing'
curl 'http://127.0.0.1:8000/facilities/search?category=bathroom&lat=-15.827&lon=-70.019&radius_m=1000'
curl 'http://127.0.0.1:8000/facilities/search?q=almuerzo'
curl 'http://127.0.0.1:8000/facilities/geojson'
```

All distance calculations use PostGIS geography in meters; distances are **straight line**, not pedestrian travel times. No student position is stored by the module. Location permission is optional in the map. To route along paths, add a real pedestrian routing engine in a future iteration.

## Operator review with local admin JWT (pilot only)

1. Bootstrap an administrator using `python -m app.accounts_cli bootstrap-admin ...` from the v0.5 account module; use a strong secret and the documented pilot login flow. Production must integrate with institutional SSO.
2. Use `GET /facilities/admin/pending` with bearer token to inspect imported facilities.
3. Verify on site: name, exact location, operating hours, accessibility, business classification, and permission to publish any contact information. Correct mistakes using the authenticated `PUT /facilities/admin/{id}` endpoint. Editing hides a record pending re-review.
4. Authorize a verified public record by `POST /facilities/admin/{id}/review` with `{"publish":true,"reason":"Verificado en campo ..."}`.
5. If closed, inaccurate, or potentially unsafe, unpublish by posting `{"publish":false,"reason":"..."}`.

To manually register a facility (starts hidden):

```bash
curl -X POST http://127.0.0.1:8000/facilities/admin \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Servicio de prueba", "category":"copies", "lat":-15.827, "lon":-70.019, "opening_hours":"por confirmar"}'
```

For safety, medical categories are **location and directory data only**, not clinical recommendations. No student medical records, test results, or diagnoses are handled. Confirm that each listed medical/testing service actually offers the claimed service.

## API endpoints

| Route | Purpose |
|---|---|
| `GET /facilities/categories` | Named categories |
| `GET /facilities/search` | Public search, distance/accessibility filters |
| `GET /facilities/geojson` | Public FeatureCollection for the app |
| `GET /facilities/{facility_id}` | Public verified facility detail |
| `POST /facilities/admin` | Create hidden operator record (admin) |
| `GET /facilities/admin/pending` | Review queue (admin/moderator) |
| `PUT /facilities/admin/{id}` | Edit and require re-review (admin) |
| `POST /facilities/admin/{id}/review` | Publish/unpublish (admin/moderator) |
| `GET /services-map` | Map/list viewer |

## Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest -q tests/test_facilities.py
# DB integration requires a running database:
PYTHONPATH=. pytest -q
```

## Integration notes

- The UI uses unauthenticated **read-only** APIs. Publishing requires roles from v0.5 and is audited to `campus_facility_audit`.
- Keep OSM attribution and comply with ODbL, including obligations applicable to derived databases.
- Never accept facility medical test results or private student locations in this module.
- Future additions: edit requests and photo verification, shop owner claims, walking navigation, campus buildings/floors, opening-hours parser, change detection, offline MBTiles and map tile hosting, student reports subject to moderation.
