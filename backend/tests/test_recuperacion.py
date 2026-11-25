"""Etapa 3 · Pruebas del sistema: RECUPERACIÓN (tema 4.3).

Se fuerza la falla de la base de datos y se comprueba que el servidor no se
cae, responde un error claro que la cola del teléfono reintenta, y vuelve a
funcionar solo, sin reiniciarlo. Los reenvíos con el mismo X-Id-Cliente no
duplican registros (la cola sin conexión ya se probó en O01-O04 y E2E-07).
"""
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import Ubicacion
from tests.conftest import cliente
from tests.escenario import iniciar_jornada, punto


@pytest.fixture
def falla(app):
    estado = {"activa": False}
    with app.app_context():
        motor = db.engine

    def _falla(*a, **k):
        if estado["activa"]:
            raise OperationalError("SELECT", {}, Exception("SQL Server no disponible (falla simulada)"))
    event.listen(motor, "before_cursor_execute", _falla)
    yield estado
    event.remove(motor, "before_cursor_execute", _falla)


def _ubic(app):
    with app.app_context():
        return db.session.execute(db.select(db.func.count()).select_from(Ubicacion)).scalar_one()


def test_REC01_base_caida_responde_json_503(app, esc, falla, obs):
    c = cliente(app, "p1@test.mx")
    iniciar_jornada(c, punto(esc.coords[0], 10))
    falla["activa"] = True
    r = obs(c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 30), headers={"X-Id-Cliente": str(uuid.uuid4())}))
    assert r.status_code == 503 and r.is_json
    assert "no puede conectarse a la base de datos" in r.get_json()["error"]


def test_REC02_se_recupera_sin_reiniciar_y_sin_duplicar(app, esc, falla, obs):
    c = cliente(app, "p1@test.mx")
    iniciar_jornada(c, punto(esc.coords[0], 10))
    antes = _ubic(app)
    ids = [str(uuid.uuid4()) for _ in range(3)]
    falla["activa"] = True
    assert all(c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 40),
                      headers={"X-Id-Cliente": i}).status_code == 503 for i in ids)
    falla["activa"] = False
    # La cola del teléfono reenvía los 3 eventos, y uno de ellos dos veces.
    for i in ids + ids[:1]:
        r = c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 40), headers={"X-Id-Cliente": i})
        assert r.status_code in (200, 201)
    obs(r)
    assert _ubic(app) - antes == 3
    assert c.get("/api/promotor/hoy").status_code == 200
