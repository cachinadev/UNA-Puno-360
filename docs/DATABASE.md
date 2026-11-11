# Base de datos

PostgreSQL/PostGIS se inicializa con los archivos numerados de `services/api/sql`:

| Migración | Dominio |
|---|---|
| `001_init.sql` | PostGIS, lugares y registros académicos |
| `002_services.sql` | bibliotecas, libros, comedores, menús y anuncios |
| `003_community.sql` | usuarios, grupos, membresías, publicaciones, comentarios, reacciones, eventos y reportes |
| `004_accounts.sql` | correo, credenciales Argon2id, sesiones, tokens de un uso y auditoría |
| `005_transport.sql` | rutas, paradas, vehículos, posiciones y auditoría de ingesta |
| `006_services_finder.sql` | instalaciones, verificación y auditoría |

Los campos espaciales usan SRID 4326 e índices GiST. Las consultas de distancia convierten a `geography` y devuelven metros en línea recta.

## Respaldo antes de actualizar

```powershell
New-Item -ItemType Directory -Force database\backups | Out-Null
docker compose exec -T db pg_dump -U una_user -d una_puno_360 -Fc > database\backups\una_puno_360.dump
```

No ejecute `docker compose down -v` sobre una instalación con datos. Las migraciones montadas por Compose solo se ejecutan automáticamente al crear un volumen vacío; una base existente requiere aplicar cada SQL pendiente con `psql -v ON_ERROR_STOP=1` después del respaldo.

Las contraseñas usan Argon2id. Solo hashes de refresh tokens y tokens de un uso se guardan. Los datos demo llevan fuente o nombres explícitos y no son publicables en instalaciones/servicios.
