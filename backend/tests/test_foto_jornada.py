"""Etapa 3 · RF-01 del modelo de diseño: foto del promotor al iniciar la jornada.

Diagrama de actividad RF-01: el promotor captura su fotografía de entrada;
"¿Fotografía válida?" Sí -> se guarda en BD (foto, hora y ubicación) y se
muestra "Jornada iniciada correctamente"; No -> "Fotografía no válida.
Intenta de nuevo" y la jornada no se inicia.
"""
import os
import uuid

from app.extensions import db
from app.models import Jornada
from tests.conftest import cliente
from tests.escenario import foto, iniciar_jornada, punto, subir_foto


def _jornadas(app):
    with app.app_context():
        return db.session.execute(db.select(db.func.count()).select_from(Jornada)).scalar_one()


def _archivos(app):
    base = os.path.join(app.config["EVIDENCIAS_DIR"], "jornadas")
    return sum(len(f) for _, _, f in os.walk(base)) if os.path.isdir(base) else 0


def test_FJ01_inicio_con_foto_valida(app, esc, obs):
    """FJ-01 · Éxito: foto válida dentro de la primera tienda
    Esperado: 201 "Jornada iniciada correctamente"; foto guardada con hash y
    metadatos; la ve el promotor y su supervisor, no otro supervisor."""
    c = cliente(app, "p1@test.mx")
    r = obs(iniciar_jornada(c, punto(esc.coords[0], 10)))
    assert r.status_code == 201
    assert r.get_json()["mensaje"].startswith("Jornada iniciada correctamente")
    url = r.get_json()["jornada"]["foto_inicio_url"]
    assert url and _archivos(app) == 1
    with app.app_context():
        j = db.session.execute(db.select(Jornada)).scalar_one()
        assert len(j.foto_inicio_hash) == 64 and '"fuente": "camara"' in j.foto_inicio_metadatos
    assert c.get(url).status_code == 200
    assert cliente(app, "s1@test.mx").get(url).status_code == 200     # su supervisor
    assert cliente(app, "s2@test.mx").get(url).status_code == 404     # otro supervisor
    assert cliente(app, "p2@test.mx").get(url).status_code == 404     # otro promotor


def test_FJ02_sin_foto_no_inicia(app, esc, obs):
    """FJ-02 · Fallo: sin foto -> 400 y no se crea la jornada"""
    c = cliente(app, "p1@test.mx")
    r = obs(iniciar_jornada(c, punto(esc.coords[0], 10), con_foto=False))
    assert r.status_code == 400
    assert r.get_json()["error"] == "Toma tu foto de entrada con la cámara para iniciar la jornada."
    assert _jornadas(app) == 0


def test_FJ03_archivo_que_no_es_imagen(app, esc, obs):
    """FJ-03 · Fallo: un PDF/texto renombrado .jpg -> "Fotografía no válida" """
    c = cliente(app, "p1@test.mx")
    r = obs(iniciar_jornada(c, punto(esc.coords[0], 10), datos_foto=b"%PDF-1.4 no es una foto"))
    assert r.status_code == 400 and r.get_json()["error"].startswith("Fotografía no válida")
    assert _jornadas(app) == 0 and _archivos(app) == 0


def test_FJ04_foto_mayor_a_5_mb(app, esc, obs):
    """FJ-04 · Valor límite: 5 MB + 1 byte -> 413"""
    c = cliente(app, "p1@test.mx")
    grande = b"\xff\xd8\xff\xe0" + os.urandom(5 * 1024 * 1024 - 3)
    r = obs(iniciar_jornada(c, punto(esc.coords[0], 10), datos_foto=grande))
    assert r.status_code == 413 and _jornadas(app) == 0


def test_FJ05_foto_repetida(app, esc, obs):
    """FJ-05 · Fallo: la misma imagen que ya usó otro promotor -> rechazada"""
    misma = foto()
    assert iniciar_jornada(cliente(app, "p3@test.mx"), punto(esc.coords[2], 5), datos_foto=misma).status_code == 201
    r = obs(iniciar_jornada(cliente(app, "p1@test.mx"), punto(esc.coords[0], 10), datos_foto=misma))
    assert r.status_code == 400 and "ya se había enviado" in r.get_json()["error"]
    assert _jornadas(app) == 1


def test_FJ06_foto_de_jornada_no_sirve_como_evidencia(app, esc, obs):
    """FJ-06 · La foto de entrada no puede reutilizarse como evidencia de tienda"""
    c = cliente(app, "p1@test.mx")
    misma = foto()
    iniciar_jornada(c, punto(esc.coords[0], 10), datos_foto=misma)
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    v = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 10)})
    r = obs(subir_foto(c, v.get_json()["visita"]["id_visita"], "Precios", punto(esc.coords[0], 10), datos=misma))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Rechazada"


def test_FJ07_fuera_de_geocerca_no_guarda_foto(app, esc, obs):
    """FJ-07 · Fallo: con foto válida pero a 120 m -> 409 y la foto NO se guarda"""
    c = cliente(app, "p1@test.mx")
    r = obs(iniciar_jornada(c, punto(esc.coords[0], 120)))
    assert r.status_code == 409 and _jornadas(app) == 0 and _archivos(app) == 0


def test_FJ08_sin_conexion_y_reintento(app, esc, obs):
    """FJ-08 · Sin conexión: el evento llega después con su hora de captura;
    si se reenvía con el mismo X-Id-Cliente no se duplica"""
    c = cliente(app, "p1@test.mx")
    cab = {"X-Origen": "sin-conexion", "X-Id-Cliente": str(uuid.uuid4())}
    datos = {**punto(esc.coords[0], 10), "capturado_en": "2026-11-04T08:05:00"}
    misma = foto()
    r1 = obs(iniciar_jornada(c, datos, headers=cab, datos_foto=misma))
    r2 = iniciar_jornada(c, datos, headers=cab, datos_foto=misma)
    assert r1.status_code == 201 and r2.status_code == 201 and r2.get_json().get("repetido") is True
    assert r1.get_json()["jornada"]["origen"] == "Sin conexión"
    assert _jornadas(app) == 1 and _archivos(app) == 1
