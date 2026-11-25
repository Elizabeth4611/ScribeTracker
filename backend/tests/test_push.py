"""Etapa 3 · RF-11: alertas críticas como notificación push (Web Push).

Unidad: claves VAPID, suscripción, cifrado real del mensaje (se descifra con
la clave del "navegador" de prueba). Integración: una incidencia crítica
creada por el sistema llega solo al supervisor de ese promotor.
"""
import base64
import json
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.extensions import db
from app.models import SuscripcionPush
from tests.conftest import cliente
from tests.escenario import iniciar_jornada, punto, subir_foto

ENDPOINT = "https://push.ejemplo.test/envio/"


def b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def navegador():
    """Claves que generaría un navegador al suscribirse."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    return priv, {"p256dh": b64(pub), "auth": b64(auth)}, auth


@pytest.fixture
def enviados(app, tmp_path, monkeypatch):
    """Sustituye el envío por uno que registra a quién se mandó."""
    app.config["PUSH_SINCRONO"] = True
    monkeypatch.setattr(app, "instance_path", str(tmp_path))
    lista = []
    app.extensions["st_push_enviar"] = lambda sub, carga: (lista.append((sub["endpoint"], carga)), 201)[1]
    return lista


def _suscribir(c, n):
    _, keys, _ = navegador()
    return c.post("/api/push/suscribir", json={"endpoint": f"{ENDPOINT}{n}", "keys": keys})


def test_PUSH01_clave_publica_vapid(app, esc, enviados):
    r = cliente(app, "s1@test.mx").get("/api/push/clave")
    clave = r.get_json()["clave_publica"]
    raw = base64.urlsafe_b64decode(clave + "=")
    assert r.status_code == 200 and len(raw) == 65 and raw[0] == 4   # punto P-256 sin comprimir
    assert cliente(app, "s2@test.mx").get("/api/push/clave").get_json()["clave_publica"] == clave  # misma clave


def test_PUSH02_suscripcion_valida_e_invalida(app, esc, enviados, obs):
    s1 = cliente(app, "s1@test.mx")
    assert obs(_suscribir(s1, "s1")).status_code == 201
    assert s1.post("/api/push/suscribir", json={"endpoint": "http://inseguro.test/x", "keys": {"p256dh": "a", "auth": "b"}}).status_code == 400
    assert s1.post("/api/push/suscribir", json={"endpoint": ENDPOINT + "z"}).status_code == 400
    assert cliente(app, "p1@test.mx").post("/api/push/suscribir", json={}).status_code == 403


def test_PUSH03_incidencia_critica_llega_solo_a_su_supervisor(app, esc, enviados, obs):
    _suscribir(cliente(app, "s1@test.mx"), "s1")
    _suscribir(cliente(app, "s2@test.mx"), "s2")
    c = cliente(app, "p1@test.mx")
    iniciar_jornada(c, punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 10)}).get_json()["visita"]["id_visita"]
    assert enviados == []   # iniciar y hacer check-in no son críticos
    obs(subir_foto(c, idv, "Precios", punto(esc.coords[0], 400)))   # foto fuera de geocerca = crítica
    assert len(enviados) == 1
    destino, carga = enviados[0]
    assert destino == ENDPOINT + "s1"
    assert carga["titulo"] == "Alerta crítica: Foto fuera de geocerca" and "Marco Promotor" in carga["cuerpo"]


def test_PUSH04_incidencia_no_critica_no_notifica(app, esc, enviados):
    _suscribir(cliente(app, "s1@test.mx"), "s1")
    esc.e.a_las(9, 30)   # retardo: incidencia NO crítica
    iniciar_jornada(cliente(app, "p1@test.mx"), punto(esc.coords[0], 10))
    assert enviados == []


def test_PUSH05_suscripcion_vencida_se_borra(app, esc, enviados):
    s1 = cliente(app, "s1@test.mx")
    _suscribir(s1, "s1")
    app.extensions["st_push_enviar"] = lambda sub, carga: 410
    assert s1.post("/api/push/probar").status_code == 200
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(SuscripcionPush)).scalar_one() == 0


def test_PUSH06_probar_sin_suscripcion(app, esc, enviados, obs):
    r = obs(cliente(app, "s1@test.mx").post("/api/push/probar"))
    assert r.status_code == 409


def test_PUSH07_cifrado_real_y_firma_vapid(app, esc, tmp_path, monkeypatch):
    """Sin red: se intercepta la petición HTTP y se descifra el mensaje con la
    clave privada del navegador de prueba (RFC 8291, aes128gcm)."""
    import http_ece
    import requests
    from app.servicios import push
    monkeypatch.setattr(app, "instance_path", str(tmp_path))
    priv, keys, auth = navegador()
    capturado = {}

    class Resp:
        status_code = 201
        text = ""

    def falso_post(url, data=None, headers=None, timeout=None, **kw):
        capturado.update(url=url, data=data, headers=headers)
        return Resp()

    monkeypatch.setattr(requests, "post", falso_post)
    with app.app_context():
        codigo = push.enviar_a({"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": keys},
                               {"titulo": "Prueba", "cuerpo": "Hola supervisor"})
    assert codigo == 201
    assert capturado["headers"]["content-encoding"] == "aes128gcm"
    assert capturado["headers"]["authorization"].startswith("vapid t=")
    claro = http_ece.decrypt(capturado["data"], private_key=priv, auth_secret=auth, version="aes128gcm")
    assert json.loads(claro) == {"titulo": "Prueba", "cuerpo": "Hola supervisor"}
