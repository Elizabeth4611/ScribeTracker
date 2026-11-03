"""Respalda la base de datos de SQL Server y aplica las migraciones.

1. BACKUP DATABASE (COPY_ONLY) en la carpeta de respaldos de SQL Server.
2. Cuenta los registros de Usuario antes y después para comprobar que se
   conservan.
3. flask db upgrade (Alembic) hasta la última versión.
4. Crea los parámetros globales con su valor por defecto.
No muestra contraseñas, hashes ni el contenido de .env.
"""
import os
import sys
from datetime import datetime

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
os.chdir(BACKEND)

from flask_migrate import upgrade  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.servicios import parametros  # noqa: E402

app = create_app()
with app.app_context():
    nombre_bd = db.session.execute(text("SELECT DB_NAME()")).scalar_one()
    collation = db.session.execute(text("SELECT CONVERT(varchar(100), DATABASEPROPERTYEX(DB_NAME(), 'Collation'))")).scalar_one()
    version = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    usuarios_antes = db.session.execute(text("SELECT COUNT(*) FROM Usuario")).scalar_one()
    print(f"Base de datos: {nombre_bd} | Collation: {collation}")
    print(f"Versión de migración actual: {version}")
    print(f"Usuarios antes de migrar: {usuarios_antes}")
    db.session.commit()

    archivo = f"{nombre_bd}_antes_etapa2_{datetime.now():%Y%m%d_%H%M%S}.bak"
    raw = db.engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True
        cur = raw.cursor()
        cur.execute(f"BACKUP DATABASE [{nombre_bd}] TO DISK = N'{archivo}' WITH COPY_ONLY, INIT")
        while cur.nextset():
            pass
        cur.execute("SELECT TOP 1 physical_device_name FROM msdb.dbo.backupmediafamily f "
                    "JOIN msdb.dbo.backupset s ON s.media_set_id = f.media_set_id "
                    "WHERE s.database_name = ? ORDER BY s.backup_finish_date DESC", nombre_bd)
        print(f"RESPALDO OK: {cur.fetchone()[0]}")
    finally:
        raw.close()

    upgrade(directory="migrations")
    version = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    usuarios_despues = db.session.execute(text("SELECT COUNT(*) FROM Usuario")).scalar_one()
    tablas = db.session.execute(text("SELECT name FROM sys.tables ORDER BY name")).scalars().all()
    print(f"Versión de migración final: {version}")
    print(f"Usuarios después de migrar: {usuarios_despues} ({'CONSERVADOS' if usuarios_despues == usuarios_antes else 'REVISAR'})")
    print(f"Tablas: {', '.join(tablas)}")
    print(f"Parámetros creados: {parametros.sembrar()}")

    # Comprobación de acentos con la collation de la base
    prueba = db.session.execute(text("SELECT CASE WHEN N'Válida' = CONVERT(varchar(20), N'Válida') THEN 1 ELSE 0 END")).scalar_one()
    print(f"Acentos en VARCHAR: {'OK' if prueba == 1 else 'PROBLEMA: la collation no admite acentos'}")
