
"""
UNA Puno 360 - PostgreSQL Role Repair
Compatible with PostgreSQL 18 and Psycopg 3.

Repairs a local development role and database using DATABASE_URL.

Security:
- Administrator password is requested using getpass.
- Passwords are never printed or passed through command-line arguments.
- SQL identifiers use psycopg.sql.Identifier.
- Role passwords use psycopg.sql.Literal because CREATE/ALTER ROLE
  do not accept standard bind parameters in PASSWORD clauses.
- Existing databases and tables are not deleted.
"""

from __future__ import annotations

import argparse
import getpass
import os
from urllib.parse import unquote, urlparse

import psycopg
from psycopg import sql


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair UNA Puno 360 PostgreSQL role and database."
    )

    parser.add_argument(
        "--admin-user",
        default="postgres",
        help="PostgreSQL administrator username",
    )

    parser.add_argument(
        "--maintenance-db",
        default="postgres",
        help="Maintenance database",
    )

    args = parser.parse_args()

    # -------------------------------------------------
    # 1. Read application database configuration
    # -------------------------------------------------

    raw_url = os.environ.get("DATABASE_URL")

    if not raw_url:
        raise SystemExit(
            "ERROR: DATABASE_URL no está configurado."
        )

    target = urlparse(raw_url)

    if (
        not target.hostname
        or not target.username
        or target.password is None
    ):
        raise SystemExit(
            "ERROR: DATABASE_URL debe contener host, "
            "usuario y contraseña."
        )

    app_user = unquote(target.username)
    app_password = unquote(target.password)
    database = unquote(target.path.lstrip("/"))
    port = target.port or 5432

    if not database:
        raise SystemExit(
            "ERROR: DATABASE_URL no contiene una base de datos."
        )

    # Prevent accidental modifications of administrator roles.

    if app_user.lower() in {"postgres", args.admin_user.lower()}:
        raise SystemExit(
            "ERROR: DATABASE_URL utiliza una cuenta administradora. "
            "Configura un usuario independiente para la aplicación."
        )

    if database == args.maintenance_db:
        raise SystemExit(
            "ERROR: La base de aplicación no debe ser "
            "la base de mantenimiento."
        )

    print("=" * 55)
    print("UNA PUNO 360 - PostgreSQL Database Repair")
    print("=" * 55)

    print(f"Servidor: {target.hostname}:{port}")
    print(f"Base de datos: {database}")
    print(f"Usuario aplicación: {app_user}")

    # -------------------------------------------------
    # 2. Administrator authentication
    # -------------------------------------------------

    admin_password = getpass.getpass(
        f"Contraseña del superusuario PostgreSQL "
        f"'{args.admin_user}' (no se mostrará): "
    )

    try:
        admin = psycopg.connect(
            host=target.hostname,
            port=port,
            dbname=args.maintenance_db,
            user=args.admin_user,
            password=admin_password,
            autocommit=True,
            connect_timeout=5,
        )

        print("[OK] Autenticación administrativa correcta.")

    except psycopg.Error as exc:
        raise SystemExit(
            "ERROR: No se pudo autenticar al administrador: "
            f"{exc.diag.message_primary or type(exc).__name__}"
        ) from None

    # -------------------------------------------------
    # 3. Create or repair application role
    # -------------------------------------------------

    try:
        with admin.cursor() as cursor:

            cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s",
                (app_user,),
            )

            role_exists = cursor.fetchone() is not None

            if role_exists:

                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} "
                        "LOGIN "
                        "NOSUPERUSER "
                        "NOCREATEROLE "
                        "NOCREATEDB "
                        "PASSWORD {}"
                    ).format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )

                print(f"[OK] Rol reparado: {app_user}")

            else:

                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} "
                        "LOGIN "
                        "NOSUPERUSER "
                        "NOCREATEROLE "
                        "NOCREATEDB "
                        "PASSWORD {}"
                    ).format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )

                print(f"[OK] Rol creado: {app_user}")

            # -----------------------------------------
            # 4. Create or verify database
            # -----------------------------------------

            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database,),
            )

            database_exists = cursor.fetchone() is not None

            if database_exists:

                # Only change ownership when needed.
                cursor.execute(
                    """
                    SELECT pg_get_userbyid(datdba)
                    FROM pg_database
                    WHERE datname = %s
                    """,
                    (database,),
                )

                current_owner = cursor.fetchone()[0]

                if current_owner != app_user:

                    print(
                        f"[INFO] Propietario actual: {current_owner}"
                    )

                    cursor.execute(
                        sql.SQL(
                            "ALTER DATABASE {} OWNER TO {}"
                        ).format(
                            sql.Identifier(database),
                            sql.Identifier(app_user),
                        )
                    )

                    print(
                        f"[OK] Propietario actualizado: "
                        f"{database} -> {app_user}"
                    )

                else:
                    print(
                        f"[OK] Propietario correcto: {app_user}"
                    )

            else:

                cursor.execute(
                    sql.SQL(
                        "CREATE DATABASE {} OWNER {}"
                    ).format(
                        sql.Identifier(database),
                        sql.Identifier(app_user),
                    )
                )

                print(f"[OK] Base creada: {database}")

    except psycopg.Error as exc:
        raise SystemExit(
            "ERROR: No se pudo reparar rol/base: "
            f"{exc.diag.message_primary or type(exc).__name__}"
        ) from None

    finally:
        admin.close()

    # -------------------------------------------------
    # 5. Enable PostGIS
    # -------------------------------------------------

    try:
        with psycopg.connect(
            host=target.hostname,
            port=port,
            dbname=database,
            user=args.admin_user,
            password=admin_password,
            autocommit=True,
            connect_timeout=5,
        ) as database_admin:

            with database_admin.cursor() as cursor:

                cursor.execute(
                    "CREATE EXTENSION IF NOT EXISTS postgis"
                )

                cursor.execute(
                    "SELECT PostGIS_Version()"
                )

                version = cursor.fetchone()[0]

                print(f"[OK] PostGIS habilitado: {version}")

    except psycopg.Error as exc:
        raise SystemExit(
            "ERROR: Rol y base preparados, "
            "pero no se pudo habilitar PostGIS. "
            "Verifica que PostGIS esté instalado "
            "para PostgreSQL 18. Detalle: "
            f"{exc.diag.message_primary or type(exc).__name__}"
        ) from None

    # -------------------------------------------------
    # 6. Verify application connection
    # -------------------------------------------------

    try:
        with psycopg.connect(
            host=target.hostname,
            port=port,
            dbname=database,
            user=app_user,
            password=app_password,
            connect_timeout=5,
        ) as app_connection:

            with app_connection.cursor() as cursor:

                cursor.execute(
                    "SELECT current_user, current_database()"
                )

                connected_user, connected_database = cursor.fetchone()

                print("[OK] Conexión aplicación verificada.")
                print(f"     Usuario: {connected_user}")
                print(f"     Database: {connected_database}")

    except psycopg.Error as exc:
        raise SystemExit(
            "ERROR: La configuración administrativa terminó, "
            "pero la conexión con el usuario de aplicación falló: "
            f"{exc.diag.message_primary or type(exc).__name__}"
        ) from None

    print("=" * 55)
    print("UNA PUNO 360 - DATABASE REPAIR COMPLETED")
    print("=" * 55)


if __name__ == "__main__":
    main()
