"""Pruebas de tiendas (RF-19, RF-20, RF-21) y rutas/asignaciones (RF-09)."""
from datetime import timedelta

from app.extensions import db
from app.models import Asignacion
from tests.conftest import cliente
from tests.escenario import HOY

TIENDA = {"nombre_comercial": "Office Max", "cadena": "Office Max", "sucursal": "Las Torres",
          "direccion_completa": "Blvd. Las Torres 123, León", "zona": "Sur", "latitud": "21.0950",
          "longitud": "-101.6400", "radio_geocerca_m": 60, "tiempo_estimado_min": 90}


def test_T01_alta_tienda_valida(app, esc, obs):
    """T01 · Registrar tienda con coordenadas, radio y tiempo estimado
    RF: RF-19 Agregar tiendas
    Tipo: válido
    Pre: sesión de Administrador
    Entrada: Office Max Las Torres, lat 21.0950, lon -101.6400, radio 60 m, 90 min
    Esperado: HTTP 201 "Tienda registrada correctamente", estatus Activa
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/tiendas", json=TIENDA))
    assert r.status_code == 201 and r.get_json()["tienda"]["estatus"] == "Activa"
    assert r.get_json()["tienda"]["radio_geocerca_m"] == 60


def test_T02_coordenadas_obligatorias(app, esc, obs):
    """T02 · Tienda sin coordenadas y con radio fuera de rango
    RF: RF-19; excepción del modelo de diseño ("Las coordenadas GPS son obligatorias...")
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: latitud vacía, longitud 500, radio 5 m
    Esperado: HTTP 400 con mensaje en latitud, longitud y radio
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/tiendas", json={**TIENDA, "latitud": "", "longitud": "500",
                                                                      "radio_geocerca_m": 5}))
    assert r.status_code == 400
    campos = r.get_json()["campos"]
    assert "obligatorias" in campos["latitud"] and "longitud" in campos and "radio_geocerca_m" in campos


def test_T03_filtros_listado(app, esc, obs):
    """T03 · Listado de tiendas con filtros por cadena, zona y estado
    RF: RF-20 Consultar/Ver listado de tiendas
    Tipo: válido
    Pre: 4 tiendas (2 de cadena Walmart; 3 en zona Norte)
    Entrada: ?cadena=Walmart y ?zona=Norte&estatus=Activa y ?q=soriana
    Esperado: 2, 3 y 1 resultados respectivamente
    """
    c = cliente(app, "s1@test.mx")
    assert c.get("/api/tiendas?cadena=Walmart").get_json()["total"] == 2
    assert c.get("/api/tiendas?zona=Norte&estatus=Activa").get_json()["total"] == 3
    r = obs(c.get("/api/tiendas?q=soriana"))
    assert r.get_json()["total"] == 1


def test_T04_no_desactivar_tienda_programada(app, esc, obs):
    """T04 · No se desactiva una tienda con visitas programadas
    RF: RF-21 Eliminar/Desactivar tiendas (excepción del modelo de diseño)
    Tipo: inválido (estado incompatible)
    Pre: Walmart Torres Landa asignada hoy a P1 sin visita
    Entrada: POST /api/tiendas/{Walmart}/desactivar
    Esperado: HTTP 409 "No se puede desactivar porque está asignada..."
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/tiendas/{esc.ids.t[0]}/desactivar"))
    assert r.status_code == 409 and r.get_json()["asignaciones_pendientes"] == 1


def test_T05_baja_logica_tienda(app, esc, obs):
    """T05 · Baja lógica de una tienda sin asignaciones y exclusión de futuras rutas
    RF: RF-21
    Tipo: válido
    Pre: Bodega Aurrera sin asignaciones
    Entrada: desactivar y luego intentar asignarla a P2 para mañana
    Esperado: 200 al desactivar (registro conservado); 400 al asignarla ("tiendas inactivas")
    """
    admin = cliente(app, "admin@test.mx")
    r = obs(admin.post(f"/api/tiendas/{esc.ids.t[3]}/desactivar"))
    assert r.status_code == 200 and r.get_json()["tienda"]["estatus"] == "Inactiva"
    r = cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p2, "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[3]]})
    assert r.status_code == 400 and "inactivas" in r.get_json()["error"]


def test_T06_tiendas_solo_admin_escribe(app, esc, obs):
    """T06 · Supervisor no puede crear ni editar tiendas
    RF: RF-19 (actor Administrador); RNF-16
    Tipo: no autorizado
    Pre: sesión de Supervisor S1
    Entrada: POST /api/tiendas
    Esperado: HTTP 403
    """
    r = obs(cliente(app, "s1@test.mx").post("/api/tiendas", json=TIENDA))
    assert r.status_code == 403


def test_R01_asignar_dia_con_historial(app, esc, obs):
    """R01 · Asignar tiendas por fecha y orden conservando historial
    RF: RF-09 Asignación y gestión de rutas
    Tipo: válido
    Pre: P1 tiene mañana sin asignaciones
    Entrada: asignar [Office Depot, Soriana, Walmart]; luego cambiar a [Walmart, Soriana]
    Esperado: 3 asignaciones activas con orden 1-2-3; después Office Depot queda Cancelada y el orden es 1-2
    """
    c = cliente(app, "s1@test.mx")
    manana = (HOY + timedelta(days=1)).isoformat()
    t = esc.ids.t
    assert c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p1, "fecha": manana,
                                                "tiendas": [t[2], t[1], t[0]]}).status_code == 200
    r = obs(c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p1, "fecha": manana, "tiendas": [t[0], t[1]]}))
    assert r.status_code == 200
    activas = c.get(f"/api/asignaciones?id_promotor={esc.ids.p1}&fecha={manana}").get_json()["asignaciones"]
    assert [(a["tienda"]["id_tienda"], a["orden_visita"]) for a in activas] == [(t[0], 1), (t[1], 2)]
    todas = c.get(f"/api/asignaciones?id_promotor={esc.ids.p1}&fecha={manana}&historial=1").get_json()["asignaciones"]
    assert [a["estado"] for a in todas if a["tienda"]["id_tienda"] == t[2]] == ["Cancelada"]


def test_R02_cantidad_sugerida_no_bloquea(app, esc, obs):
    """R02 · Cantidad de tiendas fuera de 3-4 genera advertencia, no bloqueo
    RF: RF-09 (3 a 4 tiendas) frente a entrevista P10 (tiendas de 5 horas)
    Tipo: válido (regla flexible)
    Pre: sesión de S1
    Entrada: asignar 1 sola tienda a P2 para mañana
    Esperado: HTTP 200 con advertencia sobre la cantidad sugerida
    """
    r = obs(cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p2, "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 200 and any("sugieren" in a for a in r.get_json()["advertencias"])


def test_R03_supervisor_fuera_de_alcance(app, esc, obs):
    """R03 · Supervisor no puede asignar ni consultar promotores ajenos
    RF: RF-09; RNF-16 (supervisor limitado a su ámbito)
    Tipo: no autorizado (petición manipulada)
    Pre: P3 pertenece a S2
    Entrada: S1 envía PUT /api/asignaciones/dia y GET /api/asignaciones para P3
    Esperado: HTTP 404 en ambos; no se crean asignaciones
    """
    c = cliente(app, "s1@test.mx")
    r = obs(c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p3,
                                                 "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 404
    assert c.get(f"/api/asignaciones?id_promotor={esc.ids.p3}&fecha={HOY}").status_code == 404


def test_R04_no_modificar_dias_pasados(app, esc, obs):
    """R04 · Las asignaciones de días pasados no se modifican
    RF: RF-09 (historial)
    Tipo: inválido
    Pre: hoy es 4-nov-2026
    Entrada: guardar asignación para el 3-nov-2026
    Esperado: HTTP 409
    """
    r = obs(cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p1, "fecha": (HOY - timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 409


def test_R05_ruta_plantilla_y_aplicar(app, esc, obs):
    """R05 · Crear ruta (plantilla) y aplicarla a un rango de fechas
    RF: RF-09; prototipo admin "Crear una ruta" (nombre, promotor, días, tiendas)
    Tipo: válido
    Pre: P2 sin asignaciones
    Entrada: ruta "Zona Norte" LUN-MIE-VIE con 3 tiendas; aplicar del 9 al 15 de nov (lun a dom)
    Esperado: ruta Activa; 3 días creados (9, 11 y 13), 3 asignaciones por día con orden 1-3
    """
    c = cliente(app, "admin@test.mx")
    t = esc.ids.t
    r = c.post("/api/rutas", json={"nombre_ruta": "Zona Norte", "id_promotor": esc.ids.p2,
                                   "dias_programados": ["LUN", "MIE", "VIE"], "tiendas": [t[0], t[1], t[2]]})
    assert r.status_code == 201
    idr = r.get_json()["ruta"]["id_ruta"]
    r = obs(c.post(f"/api/rutas/{idr}/aplicar", json={"desde": "2026-11-09", "hasta": "2026-11-15"}))
    assert r.get_json()["dias_creados"] == 3
    with app.app_context():
        filas = db.session.execute(db.select(Asignacion.fecha, Asignacion.orden_visita).where(
            Asignacion.id_promotor == esc.ids.p2).order_by(Asignacion.fecha, Asignacion.orden_visita)).all()
        assert len(filas) == 9 and {f[0].day for f in filas} == {9, 11, 13}


def test_R06_ruta_sin_dias_ni_tiendas(app, esc, obs):
    """R06 · Ruta sin días ni tiendas
    RF: RF-09; RF-23 mensajes de error
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: nombre vacío, días [], tiendas []
    Esperado: HTTP 400 con mensajes en nombre_ruta, dias_programados y tiendas
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/rutas", json={"id_promotor": esc.ids.p2, "nombre_ruta": "",
                                                                    "dias_programados": [], "tiendas": []}))
    assert r.status_code == 400 and set(r.get_json()["campos"]) == {"nombre_ruta", "dias_programados", "tiendas"}
