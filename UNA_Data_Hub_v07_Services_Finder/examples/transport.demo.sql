-- Coordinates are fictional test data near Puno, NOT published bus routes or real vehicles.
INSERT INTO transport_routes(id,name,service_type,description,official_verified,public_enabled,shape)
 VALUES ('DEMO-UNA-1','Ruta de prueba (NO OFICIAL)','urban','Datos sintéticos exclusivamente',false,true,
 ST_GeomFromText('LINESTRING(-70.020 -15.830,-70.015 -15.825,-70.010 -15.820)',4326))
 ON CONFLICT(id) DO NOTHING;
INSERT INTO transport_stops(id,route_id,name,stop_order,position,official_verified) VALUES
 ('DEMO-S1','DEMO-UNA-1','Paradero ficticio A',0,ST_SetSRID(ST_MakePoint(-70.020,-15.830),4326),false),
 ('DEMO-S2','DEMO-UNA-1','Paradero ficticio B',1,ST_SetSRID(ST_MakePoint(-70.015,-15.825),4326),false)
 ON CONFLICT(id) DO NOTHING;
INSERT INTO transport_vehicles(id,tenant,public_label,provider,provider_vehicle_id,route_id,public_enabled)
 VALUES ('DEMO-BUS-1','una','Vehículo DEMO (no real)','demo','demo-001','DEMO-UNA-1',true)
 ON CONFLICT(id) DO NOTHING;
