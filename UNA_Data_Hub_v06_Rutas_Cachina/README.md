# UNA Data Hub v0.6 — UNA Rutas ↔ CACHINA

Prototype assembled on the complete v0.5 project. Not an official UNA service. This release never assumes real upstream API endpoints on kuntur.cachina.pe or rutas.cachina.pe.

## Architecture
GPS units → CACHINA KUNTUR (telematics) → approved server-to-server bridge → UNA Data Hub PostGIS → `/transport/*` public REST → UNA Conecta app.

`rutas.cachina.pe` can provide verified static route geometries and stops when a documented export or API is made available. Currently the public Rutas page labels some trajectories and animated vehicles as demo, not live GPS; do not ingest those as genuine vehicle positions.

## Run
1. `cp .env.example .env`; change PostgreSQL and DATABASE_URL, AUTH secrets and TRANSPORT secrets. Generate two distinct 32+ byte secrets (`openssl rand -hex 32`).
2. `docker compose up -d --build` on a NEW database. Existing v0.5 DB: preserve the same volume and apply `sql/005_transport.sql` manually (see below).
3. Test `http://127.0.0.1:8000/docs` and `/transport/routes`.
4. Optional synthetic fixture: `docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < examples/transport.demo.sql`. Never mistake DEMO routes for official routes.
5. Generate demo location: `python3 - <<'PY' > /tmp/position.json
import json,datetime
print(json.dumps(dict(provider='demo',tenant='una',positions=[dict(vehicle_id='demo-001',lat=-15.827,lon=-70.017,speed_kph=24,heading=60,observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())])))
PY`
6. `set -a; source .env; set +a; curl -s -X POST http://127.0.0.1:8000/transport/internal/ingest -H "Authorization: Bearer $TRANSPORT_BRIDGE_TOKEN" -H 'Content-Type: application/json' --data-binary @/tmp/position.json`.
7. `curl http://127.0.0.1:8000/transport/vehicles/geojson`.

## Existing database migration
First back up: `docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_before_v06.sql`.
Then: `docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/005_transport.sql`.
Avoid `docker compose down -v` as it deletes volumes. Ensure Compose uses the SAME existing project/volume when upgrading from v0.5.

## Public endpoints
- `GET /transport/routes` published routes and linestring geometry as GeoJSON.
- `GET /transport/routes/{id}/stops` published stop points.
- `GET /transport/vehicles` only mapped, explicitly published vehicles with observations fresher than 5 minutes.
- `GET /transport/vehicles/geojson` GeoJSON of fresh published positions.
- `POST /transport/internal/ingest` trusted bridge with bearer secret.
- `POST /transport/internal/webhook` signed payload with headers `X-Transport-Timestamp` (Unix seconds), `X-Transport-Signature: sha256=<hex>`, HMAC-SHA256 over `timestamp + '.' + raw body`.

## Provider adapter
`python -m app.transport_bridge` optionally polls ONE configured authorized HTTPS endpoint. Required: `TRANSPORT_PROVIDER` = `kuntur` or `rutas`, `TRANSPORT_PROVIDER_URL` = documented endpoint URL, `TRANSPORT_PROVIDER_TOKEN`, `TRANSPORT_ALLOWED_HOSTS` (exact hostname), `TRANSPORT_TENANT=una`, `TRANSPORT_BRIDGE_TOKEN`, `TRANSPORT_HUB_URL`. The adapter expects a contract `{ "vehicles": [{ "id": "...", "lat": -15.8, "lon": -70.0, "observed_at": "2026-11-10T11:00:00Z", "speed_kph": 25, "heading": 80 }] }`; **this contract is defined here, NOT claimed to exist on KUNTUR or Rutas**. Adapt `normalize` to real upstream fields after obtaining authorization.

Before production: run bridge on a private network; configure egress allowlist/firewall, DNS pinning or private endpoint to prevent rebinding; rotate secrets; ensure HTTPS, rate limits, logs without precise private trips; tenant isolation; formal consent and publication approvals from UNA; add replay protection and idempotency for the signed webhook; public feed delay/coarsening if safety policy requires. Do not export video, SOS, driver identities, or precise trip histories.

## Test
`pip install -r requirements.txt && pytest -q tests/test_transport.py` (unit tests, no Docker required); DB integration must run separately with PostgreSQL/PostGIS.
