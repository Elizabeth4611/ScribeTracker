"""REC-04 · La base de Azure en pausa: el servidor reintenta hasta que despierta."""
import pytest
from sqlalchemy import create_engine, text

from app.servicios import despertar_bd


class ErrorAzure(Exception):
    pass


def _motor(fallas, mensaje):
    engine = create_engine("sqlite://")
    real = engine.dialect.connect
    estado = {"llamadas": 0, "esperas": 0}

    def connect(*a, **k):
        estado["llamadas"] += 1
        if estado["llamadas"] <= fallas:
            raise ErrorAzure(mensaje)
        return real(*a, **k)

    engine.dialect.connect = connect
    despertar_bd.activar(engine, intentos=5, espera=0,
                         dormir=lambda s: estado.__setitem__("esperas", estado["esperas"] + 1))
    return engine, estado


def test_base_en_pausa_se_reintenta_y_conecta():
    engine, estado = _motor(3, "[40613] Database 'ScribeTracker' is not currently available.")
    with engine.connect() as c:
        assert c.execute(text("SELECT 1")).scalar() == 1
    assert estado["llamadas"] == 4 and estado["esperas"] == 3


def test_error_que_no_es_de_pausa_no_se_reintenta():
    engine, estado = _motor(1, "[18456] Login failed for user 'admin_sql'.")
    with pytest.raises(Exception, match="18456"):
        engine.connect()
    assert estado["llamadas"] == 1


def test_se_rinde_despues_de_los_intentos():
    engine, estado = _motor(99, "40613 not currently available")
    with pytest.raises(Exception, match="40613"):
        engine.connect()
    assert estado["llamadas"] == 5
