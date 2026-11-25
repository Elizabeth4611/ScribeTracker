"""Etapa 3 · RF-06 del modelo de diseño: categorías Entrada y Salida.

Clases de equivalencia de "categoría": válidas = las 6 del modelo de diseño
(Entrada, Anaquel antes, Anaquel después, Precios, Promociones, Salida);
inválidas = cualquier otro texto o vacío. Regla D: el check-out exige una
foto VÁLIDA de cada categoría.
"""
import pytest

from app.models.operacion import CATEGORIAS
from tests.conftest import cliente
from tests.escenario import iniciar_jornada, punto, subir_foto


@pytest.fixture
def visita(app, esc):
    c = cliente(app, "p1@test.mx")
    iniciar_jornada(c, punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    r = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 10)})
    return c, r.get_json()["visita"]["id_visita"]


def _checkout(c, idv, esc):
    return c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 10)})


def test_CAT01_seis_categorias_en_orden():
    assert CATEGORIAS == ("Entrada", "Anaquel antes", "Anaquel después", "Precios", "Promociones", "Salida")


@pytest.mark.parametrize("cat", ["Entrada", "Salida"])
def test_CAT02_entrada_y_salida_se_aceptan(visita, esc, obs, cat):
    c, idv = visita
    r = obs(subir_foto(c, idv, cat, punto(esc.coords[0], 5)))
    assert r.status_code == 201 and r.get_json()["mensaje"] == f"Foto guardada correctamente ({cat})."


@pytest.mark.parametrize("cat", ["Fachada", "", "entrada"])
def test_CAT03_categoria_invalida(visita, esc, obs, cat):
    c, idv = visita
    r = obs(subir_foto(c, idv, cat, punto(esc.coords[0], 5)))
    assert r.status_code == 400
    assert r.get_json()["error"] == "Selecciona una categoría: " + ", ".join(CATEGORIAS) + "."


def test_CAT04_checkout_con_5_de_6_falta_salida(visita, esc, obs):
    c, idv = visita
    for cat in CATEGORIAS[:-1]:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    r = obs(_checkout(c, idv, esc))
    assert r.status_code == 409 and r.get_json()["faltantes"] == ["Salida"]


def test_CAT05_checkout_con_las_6(visita, esc, obs):
    c, idv = visita
    for cat in CATEGORIAS:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    r = obs(_checkout(c, idv, esc))
    assert r.status_code == 200 and r.get_json()["visita"]["estado"] == "Cerrada"


def test_CAT06_salida_fuera_de_geocerca_no_cuenta(visita, esc, obs):
    c, idv = visita
    for cat in CATEGORIAS[:-1]:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    r = subir_foto(c, idv, "Salida", punto(esc.coords[0], 300))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Fuera de geocerca"
    r = obs(_checkout(c, idv, esc))
    assert r.status_code == 409 and r.get_json()["faltantes"] == ["Salida"]


def test_CAT07_sin_promocion_solo_en_promociones(visita, esc, obs):
    c, idv = visita
    r = obs(subir_foto(c, idv, "Salida", punto(esc.coords[0], 5), sin_promocion=True))
    assert r.status_code == 400 and "solo aplica a la categoría Promociones" in r.get_json()["error"]
