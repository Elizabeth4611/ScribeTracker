import pytest

from app.extensions import db
from app.models import Usuario
from tests.conftest import PASSWORD, ConfigPruebas, login


def test_login_correcto_devuelve_rol_sin_hash(client):
    r = login(client, "promotor@test.mx")
    assert r.status_code == 200
    usuario = r.get_json()["usuario"]
    assert usuario["rol"] == "Promotor"
    assert "password_hash" not in usuario
    assert "password" not in usuario
    # Corrección F01: la comprobación anterior buscaba la palabra
    # "password" en todo el texto y fallaba con la bandera booleana
    # debe_cambiar_password. Ahora se verifica lo importante: que ni la
    # contraseña ni su hash aparezcan en la respuesta.
    texto = r.get_data(as_text=True)
    assert PASSWORD not in texto
    with client.application.app_context():
        h = db.session.execute(db.select(Usuario.password_hash).where(
            Usuario.correo_electronico == "promotor@test.mx")).scalar_one()
    assert h not in texto and h.split("$")[-1] not in texto


def test_correo_sin_distinguir_mayusculas_ni_espacios(client):
    assert login(client, "  PROMOTOR@Test.mx ").status_code == 200


def test_contrasena_incorrecta(client):
    r = login(client, "promotor@test.mx", "otra-cosa")
    assert r.status_code == 401
    assert r.get_json()["error"] == "Correo o contraseña incorrectos."


def test_correo_inexistente_mismo_mensaje(client):
    r = login(client, "nadie@test.mx")
    assert r.status_code == 401
    assert r.get_json()["error"] == "Correo o contraseña incorrectos."


def test_campos_vacios(client):
    assert login(client, "", "").status_code == 400


def test_login_exige_json(client):
    r = client.post("/api/auth/login", data={"correo": "a", "password": "b"})
    assert r.status_code == 415


def test_usuario_inactivo_no_entra(client):
    r = login(client, "inactivo@test.mx")
    assert r.status_code == 403
    assert "inactiva" in r.get_json()["error"]
    assert client.get("/api/auth/me").status_code == 401


def test_inactivo_con_contrasena_mala_no_revela_estatus(client):
    r = login(client, "inactivo@test.mx", "mala-clave")
    assert r.status_code == 401


def test_me_sin_sesion(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_con_sesion(client):
    login(client, "admin@test.mx")
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.get_json()["usuario"]["rol"] == "Administrador"


def test_cookie_httponly(client):
    r = login(client, "admin@test.mx")
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_logout_cierra_sesion(client):
    login(client, "admin@test.mx")
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/inicio/administrador").status_code == 401


def test_desactivar_usuario_invalida_sesion_abierta(client, app):
    login(client, "promotor@test.mx")
    assert client.get("/api/inicio/promotor").status_code == 200
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.estatus = "Inactivo"
        db.session.commit()
    assert client.get("/api/inicio/promotor").status_code == 401


def test_cambiar_contrasena_invalida_sesion_abierta(client, app):
    login(client, "promotor@test.mx")
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.set_password("Nueva-clave-5678")
        db.session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_cambiar_rol_cambia_permisos(client, app):
    login(client, "promotor@test.mx")
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.rol = "Supervisor"
        db.session.commit()
    assert client.get("/api/inicio/promotor").status_code == 403
    assert client.get("/api/inicio/supervisor").status_code == 200


ACCESOS = {
    "Promotor": "promotor@test.mx",
    "Supervisor": "supervisor@test.mx",
    "Administrador": "admin@test.mx",
}
RUTAS = {
    "Promotor": "/api/inicio/promotor",
    "Supervisor": "/api/inicio/supervisor",
    "Administrador": "/api/inicio/administrador",
}


@pytest.mark.parametrize("rol_usuario", list(ACCESOS))
@pytest.mark.parametrize("rol_ruta", list(RUTAS))
def test_matriz_de_permisos(client, rol_usuario, rol_ruta):
    login(client, ACCESOS[rol_usuario])
    esperado = 200 if rol_usuario == rol_ruta else 403
    assert client.get(RUTAS[rol_ruta]).status_code == esperado


@pytest.mark.parametrize("ruta", list(RUTAS.values()))
def test_inicio_sin_sesion(client, ruta):
    assert client.get(ruta).status_code == 401


def test_supervisor_ve_a_sus_promotores(client):
    login(client, "supervisor@test.mx")
    datos = client.get("/api/inicio/supervisor").get_json()
    assert [p["correo_electronico"] for p in datos["promotores"]] == ["promotor@test.mx"]


def test_promotor_ve_a_su_supervisor(client):
    login(client, "promotor@test.mx")
    datos = client.get("/api/inicio/promotor").get_json()
    assert datos["supervisor"]["correo_electronico"] == "supervisor@test.mx"


def test_admin_ve_resumen(client):
    login(client, "admin@test.mx")
    datos = client.get("/api/inicio/administrador").get_json()
    assert datos["total_usuarios"] == 4
    assert datos["resumen_usuarios"]["Promotor"] == {"Activo": 1, "Inactivo": 1}


def test_sin_secret_key_no_arranca():
    class SinClave(ConfigPruebas):
        SECRET_KEY = None

    from app import create_app

    with pytest.raises(RuntimeError):
        create_app(SinClave)


def test_cookie_alterada_no_sirve(client):
    login(client, "promotor@test.mx")
    client.set_cookie("scribetracker_session", "valor.falsificado.xyz")
    assert client.get("/api/auth/me").status_code == 401
