# Base de datos

Las migraciones SQL canónicas están en `services/api/sql` porque también se incluyen en la imagen de la API. Docker Compose las monta en orden para una base nueva. No se modifican volúmenes existentes automáticamente.

Antes de migrar una instalación previa, cree un respaldo en `database/backups` con `pg_dump`. Los registros con fuente `demo` nunca deben publicarse como datos verificados.
