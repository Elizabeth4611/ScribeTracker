"""Etapa 3 · Pruebas del sistema: SEGURIDAD (tema 4.3).

Quien prueba juega el papel de alguien que quiere entrar o romper el sistema:
inyección SQL, acceso sin sesión, escalar permisos, cookie alterada, fuerza
bruta, archivos disfrazados y texto con marcas que podría romper o inyectar
contenido en los reportes PDF.
"""
import pytest

from tests.conftest import PASSWORD, cliente, login

PROTEGIDAS = [
    ("get", "/api/promotor/hoy"), ("post", "/api/promotor/jornada/iniciar"), ("get", "/api/supervision/mapa"),
    ("get", "/api/incidencias"), ("get", "/api/usuarios"), ("get", "/api/supervision/solicitudes"),
    ("post", "/api/reportes"), ("get", "/api/push/clave"), ("get", "/api/parametros"),
]


@pytest.mark.parametrize("dato", ["' OR '1'='1", "admin@test.mx' --", "x' ; DROP TABLE Usuario; --",
                                  "EMP' OR 1=1 --"])
def test_SEG01_inyeccion_sql_en_login(client, dato):
    r = client.post("/api/auth/login", json={"usuario": dato, "password": "' OR '1'='1"})
    assert r.status_code == 401
    assert login(client, "admin@test.mx").status_code == 200   # la tabla sigue intacta


@pytest.mark.parametrize("metodo,ruta", PROTEGIDAS)
def test_SEG02_sin_sesion_todo_responde_401(client, metodo, ruta):
    assert getattr(client, metodo)(ruta, json={}).status_code == 401


@pytest.mark.parametrize("ruta", ["/api/usuarios", "/api/supervision/mapa",
                                  "/api/supervision/solicitudes", "/api/push/clave"])
def test_SEG03_promotor_no_escala_permisos(app, esc, ruta):
    assert cliente(app, "p1@test.mx").get(ruta).status_code == 403


def test_SEG03b_promotor_lee_pero_no_cambia_parametros(app, esc):
    """Los parámetros se pueden LEER desde todos los roles (el celular necesita el
    intervalo de GPS), pero solo el administrador los cambia."""
    c = cliente(app, "p1@test.mx")
    assert c.get("/api/parametros").status_code == 200
    assert c.put("/api/parametros/login_bloqueo_min", json={"valor": "1"}).status_code == 403


def test_SEG04_cookie_de_otro_servidor_no_sirve(app, esc):
    """Una cookie firmada con otra SECRET_KEY no abre sesión."""
    from flask.sessions import SecureCookieSessionInterface
    from flask import Flask
    otro = Flask("atacante")
    otro.secret_key = "clave-del-atacante"
    falsa = SecureCookieSessionInterface().get_signing_serializer(otro).dumps({"id_usuario": esc.ids.admin, "huella": "x"})
    c = app.test_client()
    c.set_cookie("scribetracker_session", falsa)
    assert c.get("/api/auth/me").status_code == 401


def test_SEG05_fuerza_bruta_se_bloquea(client):
    codigos = [client.post("/api/auth/login", json={"usuario": "admin@test.mx", "password": f"intento-{i}"}).status_code
               for i in range(6)]
    assert codigos[:3] == [401, 401, 423] and set(codigos[3:]) == {423}
    assert client.post("/api/auth/login", json={"usuario": "admin@test.mx", "password": PASSWORD}).status_code == 423


def test_SEG06_respuestas_sin_datos_sensibles(app, esc):
    texto = cliente(app, "s1@test.mx").get("/api/supervision/mapa").get_data(as_text=True)
    assert "password" not in texto.lower() and "hash" not in texto.lower()


MARCAS = "Precio < 10 & oferta <b>2x1</b> <script>alert(1)</script> <font size=40>X</font>"


def test_SEG07_texto_con_marcas_no_rompe_ni_inyecta_el_pdf(app, esc, obs):
    """El motivo y la descripción los escribe el usuario. En el PDF deben salir
    como texto, sin romper la generación ni aplicar formato inyectado."""
    p1 = cliente(app, "p1@test.mx")
    s1 = cliente(app, "s1@test.mx")
    assert p1.post("/api/promotor/solicitudes", json={"tipo": "Otro", "motivo": MARCAS}).status_code == 201
    assert s1.post("/api/incidencias", json={"id_promotor": esc.ids.p1, "tipo": "Reporte <b>x</b>",
                                             "descripcion": MARCAS}).status_code == 201
    r = s1.post("/api/reportes", json={"tipo": "Diario", "contenido": "Desempeño", "fecha": "2026-11-04",
                                       "id_promotor": esc.ids.p1})
    pdf = obs(s1.get(f"/api/reportes/{r.get_json()['reporte']['id_reporte']}/pdf"))
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    from pypdf import PdfReader
    import io
    texto = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf.data)).pages)
    assert "<script>" in texto and "Precio < 10 &" in texto, \
        "El PDF interpretó las marcas del usuario: '<script>' desapareció y el formato cambió"
