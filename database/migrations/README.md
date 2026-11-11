# Migraciones canónicas

Las migraciones ejecutables se conservan en `services/api/sql` porque forman parte de la imagen FastAPI y del flujo Docker existente.

En Windows nativo, `scripts/db-native.ps1` las descubre por nombre, las aplica en orden dentro de transacciones y registra su SHA-256 en `una_schema_migrations`. No copie ni renombre SQL aplicado: el script detiene la ejecución si detecta que cambió su checksum.
