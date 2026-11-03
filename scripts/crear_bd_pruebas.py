"""Crea (si no existe) la base SEPARADA ScribeTracker_Pruebas en el mismo
SQL Server, con la misma collation, y le aplica las migraciones para
comprobar que funcionan sobre una base vacía. La base real no se toca."""
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
os.chdir(BACKEND)

from flask_migrate import upgrade  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import URL  # noqa: E402

import config  # noqa: E402

NOMBRE = os.getenv("ST_BD_PRUEBAS", "ScribeTracker_Pruebas")
if NOMBRE == os.getenv("DB_NAME"):
    sys.exit("ST_BD_PRUEBAS no puede ser la base real.")


def url(bd):
    return URL.create("mssql+pyodbc", host=os.getenv("DB_SERVER"), database=bd, query={
        "driver": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "trusted_connection": "yes", "TrustServerCertificate": "yes"})


eng = create_engine(url("master"), isolation_level="AUTOCOMMIT")
with eng.connect() as c:
    collation = c.execute(text("SELECT CONVERT(varchar(100), DATABASEPROPERTYEX(:bd, 'Collation'))"),
                          {"bd": os.getenv("DB_NAME")}).scalar_one()
    existe = c.execute(text("SELECT DB_ID(:bd)"), {"bd": NOMBRE}).scalar_one()
    if existe is None:
        c.execute(text(f"CREATE DATABASE [{NOMBRE}] COLLATE {collation}"))
        print(f"Base de pruebas creada: {NOMBRE} ({collation})")
    else:
        print(f"Base de pruebas existente: {NOMBRE}")


class ConfigBDPruebas(config.Config):
    SQLALCHEMY_DATABASE_URI = url(NOMBRE)


from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

app = create_app(ConfigBDPruebas)
with app.app_context():
    # Base limpia: se quitan tablas de ejecuciones anteriores de pytest.
    db.drop_all()
    db.session.execute(text("IF OBJECT_ID('alembic_version') IS NOT NULL DROP TABLE alembic_version"))
    db.session.execute(text("IF OBJECT_ID('Usuario') IS NOT NULL DROP TABLE Usuario"))
    db.session.commit()
    upgrade(directory="migrations")
    v = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    n = db.session.execute(text("SELECT COUNT(*) FROM sys.tables")).scalar_one()
    idx = db.session.execute(text("SELECT COUNT(*) FROM sys.indexes WHERE has_filter = 1")).scalar_one()
    print(f"MIGRACIÓN EN BASE VACÍA OK: versión {v}, {n} tablas, {idx} índices filtrados")
