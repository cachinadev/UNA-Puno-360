-- Geometrías y vehículos sintéticos cerca de Puno. NO son rutas oficiales ni GPS real.
INSERT INTO transport_routes(id,name,service_type,description,official_verified,public_enabled,shape) VALUES
 ('DEMO-UNA-1','Circuito Lago (DEMO)','urban','Recorrido ilustrativo sintético para probar el simulador.',false,true,
  ST_GeomFromText('LINESTRING(-70.0220 -15.8320,-70.0170 -15.8270,-70.0115 -15.8240,-70.0075 -15.8285,-70.0130 -15.8335,-70.0220 -15.8320)',4326)),
 ('DEMO-UNA-2','Circuito Facultades (DEMO)','urban','Recorrido ilustrativo sintético; no representa un servicio institucional.',false,true,
  ST_GeomFromText('LINESTRING(-70.0200 -15.8260,-70.0145 -15.8215,-70.0080 -15.8230,-70.0095 -15.8295,-70.0150 -15.8310,-70.0200 -15.8260)',4326)),
 ('DEMO-UNA-3','Circuito Sur (DEMO)','urban','Recorrido ilustrativo sintético usado exclusivamente en desarrollo.',false,true,
  ST_GeomFromText('LINESTRING(-70.0180 -15.8340,-70.0125 -15.8375,-70.0065 -15.8350,-70.0080 -15.8300,-70.0145 -15.8290,-70.0180 -15.8340)',4326))
ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,
 official_verified=false,public_enabled=true,shape=excluded.shape,updated_at=now();

INSERT INTO transport_stops(id,route_id,name,stop_order,position,official_verified) VALUES
 ('DEMO-S1','DEMO-UNA-1','Inicio Lago · DEMO',0,ST_SetSRID(ST_MakePoint(-70.0220,-15.8320),4326),false),
 ('DEMO-S2','DEMO-UNA-1','Mirador · DEMO',1,ST_SetSRID(ST_MakePoint(-70.0170,-15.8270),4326),false),
 ('DEMO-S3','DEMO-UNA-1','Acceso Norte · DEMO',2,ST_SetSRID(ST_MakePoint(-70.0115,-15.8240),4326),false),
 ('DEMO-S4','DEMO-UNA-1','Servicios · DEMO',3,ST_SetSRID(ST_MakePoint(-70.0130,-15.8335),4326),false),
 ('DEMO-2-S1','DEMO-UNA-2','Facultad A · DEMO',0,ST_SetSRID(ST_MakePoint(-70.0200,-15.8260),4326),false),
 ('DEMO-2-S2','DEMO-UNA-2','Laboratorios · DEMO',1,ST_SetSRID(ST_MakePoint(-70.0145,-15.8215),4326),false),
 ('DEMO-2-S3','DEMO-UNA-2','Biblioteca · DEMO',2,ST_SetSRID(ST_MakePoint(-70.0080,-15.8230),4326),false),
 ('DEMO-2-S4','DEMO-UNA-2','Comedor · DEMO',3,ST_SetSRID(ST_MakePoint(-70.0150,-15.8310),4326),false),
 ('DEMO-3-S1','DEMO-UNA-3','Terminal Sur · DEMO',0,ST_SetSRID(ST_MakePoint(-70.0180,-15.8340),4326),false),
 ('DEMO-3-S2','DEMO-UNA-3','Polideportivo · DEMO',1,ST_SetSRID(ST_MakePoint(-70.0125,-15.8375),4326),false),
 ('DEMO-3-S3','DEMO-UNA-3','Salud · DEMO',2,ST_SetSRID(ST_MakePoint(-70.0065,-15.8350),4326),false),
 ('DEMO-3-S4','DEMO-UNA-3','Administración · DEMO',3,ST_SetSRID(ST_MakePoint(-70.0145,-15.8290),4326),false)
ON CONFLICT(id) DO UPDATE SET name=excluded.name,stop_order=excluded.stop_order,
 position=excluded.position,official_verified=false;

INSERT INTO transport_vehicles(id,tenant,public_label,provider,provider_vehicle_id,route_id,public_enabled,active) VALUES
 ('DEMO-BUS-1','una','Bus demo 01','demo','demo-001','DEMO-UNA-1',true,true),
 ('DEMO-BUS-2','una','Bus demo 02','demo','demo-002','DEMO-UNA-1',true,true),
 ('DEMO-BUS-3','una','Bus demo 03','demo','demo-003','DEMO-UNA-2',true,true),
 ('DEMO-BUS-4','una','Bus demo 04','demo','demo-004','DEMO-UNA-3',true,true)
ON CONFLICT(id) DO UPDATE SET public_label=excluded.public_label,route_id=excluded.route_id,
 public_enabled=true,active=true;
