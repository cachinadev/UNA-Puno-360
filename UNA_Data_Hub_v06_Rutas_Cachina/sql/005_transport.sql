-- v0.6 Public transport only: no driver identities, raw video, SOS or private trip history.
CREATE TABLE IF NOT EXISTS transport_routes (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL DEFAULT 'una', name TEXT NOT NULL,
 service_type TEXT NOT NULL CHECK (service_type IN ('urban','interprovincial')),
 description TEXT, official_verified BOOLEAN NOT NULL DEFAULT FALSE,
 public_enabled BOOLEAN NOT NULL DEFAULT FALSE,
 shape geometry(LineString,4326), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS tr_shape_gix ON transport_routes USING GIST(shape);
CREATE TABLE IF NOT EXISTS transport_stops (
 id TEXT PRIMARY KEY, route_id TEXT NOT NULL REFERENCES transport_routes(id) ON DELETE CASCADE,
 name TEXT NOT NULL, stop_order INTEGER NOT NULL CHECK (stop_order >= 0),
 position geometry(Point,4326) NOT NULL,
 official_verified BOOLEAN NOT NULL DEFAULT FALSE,
 UNIQUE(route_id, stop_order));
CREATE INDEX IF NOT EXISTS ts_geom_gix ON transport_stops USING GIST(position);
CREATE TABLE IF NOT EXISTS transport_vehicles (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL DEFAULT 'una', public_label TEXT NOT NULL,
 provider TEXT NOT NULL CHECK (provider IN ('kuntur','rutas','demo')),
 provider_vehicle_id TEXT NOT NULL, route_id TEXT REFERENCES transport_routes(id),
 public_enabled BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT TRUE,
 UNIQUE(provider,tenant,provider_vehicle_id));
CREATE TABLE IF NOT EXISTS transport_positions (
 vehicle_id TEXT PRIMARY KEY REFERENCES transport_vehicles(id) ON DELETE CASCADE,
 position geometry(Point,4326) NOT NULL,
 speed_kph DOUBLE PRECISION CHECK(speed_kph IS NULL OR (speed_kph>=0 AND speed_kph<=180)),
 heading DOUBLE PRECISION CHECK(heading IS NULL OR (heading>=0 AND heading<360)),
 observed_at TIMESTAMPTZ NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS tp_geom_gix ON transport_positions USING GIST(position);
CREATE TABLE IF NOT EXISTS transport_ingest_audit (
 id BIGSERIAL PRIMARY KEY, provider TEXT NOT NULL, tenant TEXT NOT NULL,
 received_at TIMESTAMPTZ NOT NULL DEFAULT now(), accepted_count INTEGER NOT NULL,
 ignored_count INTEGER NOT NULL, note TEXT);
