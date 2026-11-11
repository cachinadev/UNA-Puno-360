# Seguridad

## Controles implementados

- Argon2id para contraseñas y comparación resistente a tiempo para secretos.
- Access JWT corto con issuer, audience, expiración, versión de cuenta y sesión.
- Refresh tokens aleatorios almacenados como SHA-256, rotados y revocables.
- Roles `student`, `moderator`, `admin`, `superadmin`; asignación privilegiada fuera del registro público.
- Autorización de backend y controles de pertenencia para recursos privados.
- Bloqueo temporal tras intentos fallidos y limitación por IP/ruta para autenticación.
- Tokens de verificación/reset de un uso, hasheados y con caducidad.
- Webhook HMAC con ventana temporal, lista de vehículos aprovisionados y actualizaciones monotónicas.
- CORS por origen, cabeceras defensivas, consultas parametrizadas y auditoría administrativa.
- Instalaciones importadas ocultas hasta revisión; registros demo no publicables.

## Antes de producción

Deshabilite la exposición de tokens de desarrollo y, preferentemente, el registro local. Configure correo transaccional, Redis para rate limiting distribuido, TLS en proxy inverso, CSP específica, gestor de secretos, copias cifradas, alertas, retención de auditoría y escaneo de dependencias. Complete una evaluación de privacidad y abuso con la universidad.

La ubicación del estudiante se usa solo en el cliente para consultas de cercanía y no se almacena. No deben incorporarse expedientes académicos, elegibilidad del comedor, asistencia, información socioeconómica o médica sin base legal y controles separados.

Reporte vulnerabilidades de forma privada al responsable del despliegue; no incluya secretos ni datos personales en tickets públicos.
