"""Etapa 3 · Inicio de sesión con correo o número de empleado y bloqueo.

Pruebas de caja negra: se diseñaron solo a partir de la especificación
(RF-01 de la sección 3.6 del ERS y RNF-01), sin mirar el código.

Particiones de equivalencia del campo "usuario":
  válidas   -> correo registrado · número de empleado registrado
  inválidas -> vacío · correo no registrado · número no registrado
Valores límite del bloqueo (3 intentos, 15 minutos):
  2 fallos (aún entra) · 3 fallos (bloquea) · 14:59 (sigue bloqueada) · 15:00 (se libera)
"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Usuario
from app.servicios import tiempo
from tests.conftest import PASSWORD

T0 = datetime(2026, 11, 10, 9, 0, 0)


def entrar(client, usuario, password=PASSWORD):
    return client.post("/api/auth/login", json={"usuario": usuario, "password": password})


@pytest.fixture
def con_numero(app):
    with app.app_context():
        u = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")).scalar_one()
        u.numero_empleado = "EMP-0107"
        db.session.commit()
    tiempo.fijar(T0)


# ---------------------------------------------------------- particiones

def test_cn01_entra_con_correo(client, con_numero):
    r = entrar(client, "promotor@test.mx")
    assert r.status_code == 200 and r.get_json()["usuario"]["rol"] == "Promotor"


def test_cn02_entra_con_numero_de_empleado(client, con_numero):
    r = entrar(client, "EMP-0107")
    assert r.status_code == 200 and r.get_json()["usuario"]["numero_empleado"] == "EMP-0107"


def test_cn03_campo_vacio(client, con_numero):
    r = entrar(client, "   ")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Escribe tu correo o número de empleado y tu contraseña."


@pytest.mark.parametrize("dato", ["nadie@test.mx", "EMP-9999"])
def test_cn04_usuario_no_registrado_mensaje_generico(client, con_numero, dato):
    r = entrar(client, dato)
    assert r.status_code == 401
    assert r.get_json()["error"] == "Usuario o contraseña incorrectos."


def test_cn05_campo_anterior_correo_sigue_funcionando(client, con_numero):
    r = client.post("/api/auth/login", json={"correo": "promotor@test.mx", "password": PASSWORD})
    assert r.status_code == 200


# -------------------------------------------------------- valores límite

def test_cn06_dos_fallos_aun_permite_entrar(client, con_numero):
    for _ in range(2):
        assert entrar(client, "EMP-0107", "mala-1234").status_code == 401
    r = entrar(client, "EMP-0107")
    assert r.status_code == 200


def test_cn07_tercer_fallo_bloquea_15_minutos(client, con_numero):
    entrar(client, "promotor@test.mx", "mala-1234")
    entrar(client, "promotor@test.mx", "mala-1234")
    r = entrar(client, "promotor@test.mx", "mala-1234")
    assert r.status_code == 423
    assert r.get_json()["minutos_restantes"] == 15
    assert "bloqueada" in r.get_json()["error"]


def test_cn08_bloqueada_rechaza_contrasena_correcta(client, con_numero):
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    tiempo.fijar(T0 + timedelta(minutes=14, seconds=59))
    r = entrar(client, "EMP-0107")  # correcta, y por número de empleado
    assert r.status_code == 423
    assert r.get_json()["minutos_restantes"] == 1


def test_cn09_a_los_15_minutos_se_libera(client, con_numero):
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    tiempo.fijar(T0 + timedelta(minutes=15))
    assert entrar(client, "promotor@test.mx").status_code == 200


def test_cn10_al_liberarse_el_conteo_empieza_de_cero(client, con_numero):
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    tiempo.fijar(T0 + timedelta(minutes=16))
    # Un fallo después del bloqueo no vuelve a bloquear: es el intento 1 de 3.
    assert entrar(client, "promotor@test.mx", "mala-1234").status_code == 401
    assert entrar(client, "promotor@test.mx").status_code == 200


def test_cn11_un_acierto_reinicia_el_conteo(client, con_numero):
    entrar(client, "promotor@test.mx", "mala-1234")
    entrar(client, "promotor@test.mx", "mala-1234")
    assert entrar(client, "promotor@test.mx").status_code == 200
    entrar(client, "promotor@test.mx", "mala-1234")
    entrar(client, "promotor@test.mx", "mala-1234")
    assert entrar(client, "promotor@test.mx").status_code == 200


def test_cn12_admin_desbloquea_con_contrasena_temporal(app, client, con_numero):
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    admin = app.test_client()
    assert entrar(admin, "admin@test.mx").status_code == 200
    with app.app_context():
        pid = db.session.execute(db.select(Usuario.id_usuario).where(
            Usuario.correo_electronico == "promotor@test.mx")).scalar_one()
    r = admin.post(f"/api/usuarios/{pid}/restablecer-password", json={})
    temporal = r.get_json()["acceso"]["password_temporal"]
    assert entrar(client, "EMP-0107", temporal).status_code == 200


def test_cn13_duracion_configurable(app, client, con_numero):
    admin = app.test_client()
    entrar(admin, "admin@test.mx")
    r = admin.put("/api/parametros/login_bloqueo_min", json={"valor": "5"})
    assert r.status_code == 200, r.get_json()
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    tiempo.fijar(T0 + timedelta(minutes=5))
    assert entrar(client, "promotor@test.mx").status_code == 200


def test_cn14_f09_tras_liberarse_un_error_no_vuelve_a_bloquear(app, client, con_numero):
    """Defecto F09: al vencer el bloqueo y entrar, el contador quedaba en 3."""
    for _ in range(3):
        entrar(client, "promotor@test.mx", "mala-1234")
    tiempo.fijar(T0 + timedelta(minutes=15))
    assert entrar(client, "promotor@test.mx").status_code == 200
    with app.app_context():
        assert db.session.execute(db.select(Usuario.intentos_fallidos).where(
            Usuario.correo_electronico == "promotor@test.mx")).scalar_one() == 0
    otro = app.test_client()
    assert entrar(otro, "promotor@test.mx", "mala-1234").status_code == 401
