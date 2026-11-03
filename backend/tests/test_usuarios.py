"""Pruebas del módulo de usuarios y parámetros (ERS 3.6: RF-03 a RF-07)."""
from app.extensions import db
from app.models import Asignacion, Usuario
from tests.conftest import cliente

NUEVO = {"nombre_completo": "Ana López Ruiz", "numero_empleado": "SR-101", "telefono": "4771112233",
         "correo_electronico": "ana@test.mx", "rol": "Promotor", "tipo_contrato": "Temporada"}


def test_U01_alta_usuario_valida(app, esc, obs):
    """U01 · Alta de usuario con datos válidos
    RF: RF-03 (3.6) Crear/Agregar usuarios
    Tipo: válido
    Pre: sesión de Administrador; existe el supervisor S1
    Entrada: nombre, número de empleado SR-101, teléfono, correo, rol Promotor, supervisor S1
    Esperado: HTTP 201; cuenta Activa con debe_cambiar_password; sin SMTP se entrega contraseña temporal una vez
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}))
    assert r.status_code == 201
    d = r.get_json()
    assert d["usuario"]["debe_cambiar_password"] is True and d["usuario"]["estatus"] == "Activo"
    assert d["acceso"]["envio_correo"] == "no_configurado"
    assert len(d["acceso"]["password_temporal"]) == 12
    with app.app_context():
        u = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "ana@test.mx")).scalar_one()
        assert u.password_hash.startswith("pbkdf2:") and d["acceso"]["password_temporal"] not in u.password_hash


def test_U02_campos_obligatorios(app, esc, obs):
    """U02 · Alta rechazada por campos obligatorios vacíos
    RF: RF-03 (3.6); RF-23 Mensajes de error
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: formulario vacío
    Esperado: HTTP 400 con mensaje por campo (nombre, correo, teléfono, número de empleado, rol)
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={}))
    assert r.status_code == 400
    assert set(r.get_json()["campos"]) >= {"nombre_completo", "correo_electronico", "telefono", "numero_empleado", "rol"}


def test_U03_duplicados(app, esc, obs):
    """U03 · Correo y número de empleado duplicados
    RF: RF-03 (3.6) número de empleado único; correo UNIQUE (diccionario)
    Tipo: inválido
    Pre: existe p1@test.mx con número P1
    Entrada: nuevo usuario con correo p1@test.mx y número P1
    Esperado: HTTP 400 indicando ambos duplicados; no se crea registro
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={**NUEVO, "correo_electronico": "P1@test.mx", "numero_empleado": "p1",
                                          "id_supervisor": esc.ids.s1}))
    assert r.status_code == 400
    assert "correo_electronico" in r.get_json()["campos"] and "numero_empleado" in r.get_json()["campos"]


def test_U04_promotor_requiere_supervisor(app, esc, obs):
    """U04 · Promotor sin supervisor
    RF: RF-03/RF-07 (3.6) asignar rol y supervisor
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: rol Promotor sin id_supervisor
    Esperado: HTTP 400 en el campo id_supervisor
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json=NUEVO))
    assert r.status_code == 400 and "id_supervisor" in r.get_json()["campos"]


def test_U05_solo_admin_gestiona(app, esc, obs):
    """U05 · Supervisor y promotor no pueden registrar usuarios
    RF: RF-03 (3.6); RNF-16 control de acceso por rol
    Tipo: no autorizado
    Pre: sesiones de Supervisor S1 y Promotor P1
    Entrada: POST /api/usuarios con datos válidos (petición manipulada)
    Esperado: HTTP 403 en ambos casos
    """
    for correo in ("s1@test.mx", "p1@test.mx"):
        r = obs(cliente(app, correo).post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}))
        assert r.status_code == 403


def test_U06_busqueda_y_alcance(app, esc, obs):
    """U06 · Consulta y búsqueda de usuarios con alcance por rol
    RF: RF-04 (3.6) Consultar/Ver listado de usuarios
    Tipo: válido / alcance
    Pre: S1 supervisa a P1 y P2; S2 supervisa a P3
    Entrada: admin busca "P3"; S1 lista sin filtro
    Esperado: el admin encuentra a P3 por número de empleado; S1 solo ve a P1 y P2
    """
    r = obs(cliente(app, "admin@test.mx").get("/api/usuarios?q=P3"))
    assert [u["numero_empleado"] for u in r.get_json()["usuarios"]] == ["P3"]
    r = cliente(app, "s1@test.mx").get("/api/usuarios")
    assert sorted(u["numero_empleado"] for u in r.get_json()["usuarios"]) == ["P1", "P2"]
    assert cliente(app, "s1@test.mx").get(f"/api/usuarios/{esc.ids.p3}").status_code == 404


def test_U07_editar_usuario(app, esc, obs):
    """U07 · Editar datos de un usuario
    RF: RF-05 (3.6) Editar datos de usuario
    Tipo: válido
    Pre: sesión de Administrador; P2 pertenece a S1
    Entrada: cambiar teléfono y reasignar P2 al supervisor S2
    Esperado: HTTP 200; el cambio de supervisor modifica el alcance (S2 ve a P2, S1 ya no)
    """
    c = cliente(app, "admin@test.mx")
    u = c.get(f"/api/usuarios/{esc.ids.p2}").get_json()["usuario"]
    r = obs(c.put(f"/api/usuarios/{esc.ids.p2}", json={**u, "telefono": "4779998877", "id_supervisor": esc.ids.s2}))
    assert r.status_code == 200 and r.get_json()["usuario"]["telefono"] == "4779998877"
    assert cliente(app, "s2@test.mx").get(f"/api/usuarios/{esc.ids.p2}").status_code == 200
    assert cliente(app, "s1@test.mx").get(f"/api/usuarios/{esc.ids.p2}").status_code == 404


def test_U08_baja_logica_libera_tiendas(app, esc, obs):
    """U08 · Desactivar promotor: baja lógica y liberación de tiendas
    RF: RF-06 (3.6) Eliminar/Desactivar usuarios
    Tipo: válido
    Pre: P1 tiene 2 asignaciones hoy sin visita
    Entrada: POST /api/usuarios/P1/desactivar
    Esperado: estatus Inactivo, registro conservado, asignaciones Canceladas (historial), P1 no puede entrar
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/usuarios/{esc.ids.p1}/desactivar"))
    assert r.status_code == 200 and r.get_json()["asignaciones_liberadas"] == 2
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p1).estatus == "Inactivo"
        estados = db.session.execute(db.select(Asignacion.estado).where(Asignacion.id_promotor == esc.ids.p1)).scalars().all()
        assert estados == ["Cancelada", "Cancelada"]
    r = app.test_client().post("/api/auth/login", json={"correo": "p1@test.mx", "password": "Prueba-1234"})
    assert r.status_code == 403


def test_U09_no_desactivar_supervisor_con_promotores(app, esc, obs):
    """U09 · Supervisor con promotores activos no se puede desactivar
    RF: RF-06 (3.6)
    Tipo: inválido (estado incompatible)
    Pre: S1 tiene a P1 y P2 activos
    Entrada: POST /api/usuarios/S1/desactivar
    Esperado: HTTP 409 pidiendo reasignar a los promotores
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/usuarios/{esc.ids.s1}/desactivar"))
    assert r.status_code == 409


def test_U10_contrasena_temporal_obliga_cambio(app, esc, obs):
    """U10 · La contraseña temporal obliga a cambiarla
    RF: RF-03 (3.6) entrega de acceso; RNF-16 seguridad
    Tipo: válido / restricción
    Pre: usuario recién creado con contraseña temporal
    Entrada: login con la temporal, consulta su inicio, cambia la contraseña y vuelve a consultar
    Esperado: antes del cambio HTTP 403 (codigo cambiar_password); después HTTP 200
    """
    admin = cliente(app, "admin@test.mx")
    temporal = admin.post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}).get_json()["acceso"]["password_temporal"]
    c = app.test_client()
    assert c.post("/api/auth/login", json={"correo": "ana@test.mx", "password": temporal}).status_code == 200
    assert c.get("/api/inicio/promotor").get_json()["codigo"] == "cambiar_password"
    r = obs(c.post("/api/auth/cambiar-password", json={"password_actual": temporal, "password_nueva": "NuevaClave2026"}))
    assert r.status_code == 200
    assert c.get("/api/inicio/promotor").status_code == 200


def test_U11_intentos_fallidos_se_registran(app, esc, obs):
    """U11 · Registro de intentos fallidos (política de bloqueo pendiente)
    RF: RNF-01 inicio de sesión con bloqueo tras 3 intentos (duración PENDIENTE)
    Tipo: inválido
    Pre: usuario P2 activo
    Entrada: 3 contraseñas incorrectas y luego la correcta
    Esperado: se cuentan 3 intentos; la cuenta NO se bloquea porque la duración no está definida; el contador vuelve a 0
    """
    c = app.test_client()
    for _ in range(3):
        assert c.post("/api/auth/login", json={"correo": "p2@test.mx", "password": "mala"}).status_code == 401
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p2).intentos_fallidos == 3
    r = obs(c.post("/api/auth/login", json={"correo": "p2@test.mx", "password": "Prueba-1234"}))
    assert r.status_code == 200
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p2).intentos_fallidos == 0


def test_U12_parametros_globales(app, esc, obs):
    """U12 · Consultar, modificar y restablecer parámetros globales
    RF: ERS 3.1 portal admin punto 7 (Parámetros globales); diccionario PARÁMETRO
    Tipo: válido e inválido
    Pre: sesión de Administrador
    Entrada: gps_intervalo_min = 5; luego 99 (fuera de rango); luego restablecer
    Esperado: 200 con valor 5; 400 por rango 1-10; restablecido a 10; supervisor no puede editar (403)
    """
    c = cliente(app, "admin@test.mx")
    assert len(c.get("/api/parametros").get_json()["parametros"]) >= 10
    r = obs(c.put("/api/parametros/gps_intervalo_min", json={"valor": "5"}))
    assert r.status_code == 200 and r.get_json()["parametro"]["valor_activo"] == "5"
    assert c.put("/api/parametros/gps_intervalo_min", json={"valor": "99"}).status_code == 400
    assert c.post("/api/parametros/gps_intervalo_min/restablecer").get_json()["parametro"]["valor_activo"] == "10"
    assert cliente(app, "s1@test.mx").put("/api/parametros/gps_intervalo_min", json={"valor": "5"}).status_code == 403
