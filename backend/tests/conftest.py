"""Las pruebas usan SQLite en memoria: no tocan SQL Server ni sus datos."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Usuario  # noqa: E402
from config import Config  # noqa: E402

PASSWORD = "Prueba-1234"


def _uri_pruebas():
    """SQLite en memoria por defecto. Con la variable ST_BD_PRUEBAS se usa una
    base de SQL Server SEPARADA (nunca la base real), con el mismo servidor y
    controlador de backend/.env: scripts/etapa2_bd.bat la crea y la usa."""
    nombre = os.getenv("ST_BD_PRUEBAS")
    if not nombre:
        return "sqlite:///:memory:"
    if nombre == os.getenv("DB_NAME"):
        raise RuntimeError("ST_BD_PRUEBAS no puede ser la base de datos real.")
    from sqlalchemy.engine import URL
    return URL.create("mssql+pyodbc", host=os.getenv("DB_SERVER"), database=nombre, query={
        "driver": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "trusted_connection": "yes", "TrustServerCertificate": "yes"})


class ConfigPruebas(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = _uri_pruebas()
    SECRET_KEY = "clave-solo-para-pruebas"
    # Hash rápido solo para pruebas (en producción: scrypt).
    PASSWORD_HASH_METHOD = "pbkdf2:sha256:1000"


def _crear(nombre, correo, rol, estatus="Activo", supervisor=None):
    u = Usuario(
        nombre_completo=nombre,
        correo_electronico=correo,
        rol=rol,
        estatus=estatus,
        id_supervisor=supervisor.id_usuario if supervisor else None,
    )
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def app():
    app = create_app(ConfigPruebas)
    with app.app_context():
        db.drop_all()  # por si una ejecución anterior se interrumpió
        db.create_all()
        sup = _crear("Sofía Supervisora", "supervisor@test.mx", "Supervisor")
        _crear("Pedro Promotor", "promotor@test.mx", "Promotor", supervisor=sup)
        _crear("Ana Admin", "admin@test.mx", "Administrador")
        _crear("Iván Inactivo", "inactivo@test.mx", "Promotor", estatus="Inactivo")
        db.session.remove()

    # Sin contexto abierto durante la prueba: cada petición del cliente crea
    # el suyo, igual que en el servidor real.
    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, correo, password=PASSWORD):
    return client.post("/api/auth/login", json={"correo": correo, "password": password})


@pytest.fixture(autouse=True)
def _hora_real_al_terminar():
    from app.servicios import tiempo
    yield
    tiempo.fijar(None)


@pytest.fixture
def esc(app, tmp_path):
    """Escenario operativo: 2 supervisores, 3 promotores, admin, 4 tiendas.
    P1 tiene asignadas hoy (4-nov-2026) Walmart y Soriana, en ese orden."""
    from types import SimpleNamespace
    from tests import escenario as e

    app.config["EVIDENCIAS_DIR"] = str(tmp_path / "evidencias")
    with app.app_context():
        admin = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "admin@test.mx")).scalar_one()
        s1 = e.crear_usuario("Juan Supervisor", "s1@test.mx", "Supervisor", numero="S1")
        s2 = e.crear_usuario("Laura Supervisora", "s2@test.mx", "Supervisor", numero="S2")
        p1 = e.crear_usuario("Marco Promotor", "p1@test.mx", "Promotor", sup=s1, numero="P1")
        p2 = e.crear_usuario("Julieta Promotora", "p2@test.mx", "Promotor", sup=s1, numero="P2")
        p3 = e.crear_usuario("Pablo Promotor", "p3@test.mx", "Promotor", sup=s2, numero="P3")
        t = e.crear_tiendas()
        e.asignar(p1, [t[0], t[1]], e.HOY, s1)
        e.asignar(p3, [t[2]], e.HOY, s2)
        ids = SimpleNamespace(admin=admin.id_usuario, s1=s1.id_usuario, s2=s2.id_usuario, p1=p1.id_usuario,
                              p2=p2.id_usuario, p3=p3.id_usuario, t=[x.id_tienda for x in t])
        coords = [(float(x.latitud), float(x.longitud)) for x in t]
    e.a_las(8, 5)
    return SimpleNamespace(ids=ids, coords=coords, e=e)


def cliente(app, correo):
    """Cliente de prueba con sesión iniciada para el correo indicado."""
    c = app.test_client()
    r = login(c, correo)
    assert r.status_code == 200, r.get_json()
    return c


@pytest.fixture
def obs(record_property):
    """Registra el resultado obtenido (código y mensaje) en el reporte JUnit."""
    def _obs(r, extra=""):
        cuerpo = r.get_json(silent=True) or {}
        texto = cuerpo.get("mensaje") or cuerpo.get("error") or ""
        detalle = {k: cuerpo[k] for k in ("faltantes", "pendientes", "campos", "distancia_m") if k in cuerpo}
        record_property("obtenido", f"HTTP {r.status_code} · {texto}" + (f" · {detalle}" if detalle else "")
                        + (f" · {extra}" if extra else ""))
        return r
    return _obs
