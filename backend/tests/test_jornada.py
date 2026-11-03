"""Pruebas de jornada, visitas, evidencias, pausas y seguimiento
(RF-01 a RF-08 del promotor y reglas confirmadas C1-C9)."""
from app.extensions import db
from app.models import Evidencia, Incidencia, Jornada, Ubicacion, Visita
from tests.conftest import cliente
from tests.escenario import a_las, foto, punto, subir_foto

CATS = ["Anaquel antes", "Anaquel después", "Precios", "Promociones"]


def _p1(app):
    return cliente(app, "p1@test.mx")


def _iniciar(c, esc, metros=10):
    return c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], metros))


def _asignaciones(c):
    return c.get("/api/promotor/hoy").get_json()["asignaciones"]


def _checkin(c, esc, idx=0, metros=10, cab=None):
    a = _asignaciones(c)[idx]
    return c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"],
                                                         **punto(esc.coords[idx], metros)}, headers=cab or {})


def _cuatro_fotos(c, esc, id_visita, idx=0):
    for cat in CATS:
        assert subir_foto(c, id_visita, cat, punto(esc.coords[idx], 5)).status_code == 201


def test_J01_inicio_en_primera_tienda(app, esc, obs):
    """J01 · Iniciar jornada dentro de la geocerca de la primera tienda
    RF: RF-01 Inicio de jornada; reglas C1 y C2
    Tipo: válido
    Pre: P1 con Walmart (orden 1) y Soriana (orden 2) asignadas hoy; 08:05
    Entrada: ubicación a 10 m de Walmart Torres Landa
    Esperado: HTTP 201; jornada Abierta; rastreo activo; primer punto de ubicación registrado
    """
    c = _p1(app)
    r = obs(_iniciar(c, esc))
    assert r.status_code == 201 and r.get_json()["jornada"]["estado"] == "Abierta"
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["rastreo_activo"] is True and hoy["estado"]["estado_jornada"] == "En jornada"
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Ubicacion)).scalar_one() == 1


def test_J02_inicio_fuera_de_primera_tienda(app, esc, obs):
    """J02 · Iniciar jornada fuera de la geocerca o en otra tienda asignada
    RF: RF-01; regla C2
    Tipo: inválido
    Pre: P1 sin jornada
    Entrada: (a) a 120 m de Walmart; (b) dentro de Soriana, que es la tienda 2
    Esperado: HTTP 409 en ambos casos con la distancia; no se crea jornada
    """
    c = _p1(app)
    r = obs(_iniciar(c, esc, metros=120))
    assert r.status_code == 409 and r.get_json()["distancia_m"] > 50
    assert c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[1], 5)).status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Jornada)).scalar_one() == 0


def test_J03_jornada_unica_por_fecha(app, esc, obs):
    """J03 · Una sola jornada por fecha operativa
    RF: RF-01; regla C1
    Tipo: inválido (duplicado)
    Pre: P1 ya inició y finalizó su jornada hoy (cierre forzado con motivo)
    Entrada: segundo intento de iniciar jornada el mismo día
    Esperado: HTTP 409 "Ya registraste una jornada para este día"
    """
    c = _p1(app)
    _iniciar(c, esc)
    c.post("/api/promotor/jornada/finalizar", json={**punto(esc.coords[0]), "forzar": True,
                                                   "motivo": "Prueba de jornada única"})
    r = obs(_iniciar(c, esc))
    assert r.status_code == 409 and "una jornada" in r.get_json()["error"]


def test_J04_sin_tiendas_asignadas(app, esc, obs):
    """J04 · Promotor sin tiendas asignadas no puede iniciar
    RF: RF-01 (dependencia de RF-09)
    Tipo: inválido
    Pre: P2 no tiene asignaciones hoy
    Entrada: iniciar jornada en cualquier punto
    Esperado: HTTP 409 "No tienes tiendas asignadas para hoy"
    """
    r = obs(cliente(app, "p2@test.mx").post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0])))
    assert r.status_code == 409 and "asignadas" in r.get_json()["error"]


def test_J05_retardo_registrado(app, esc, obs):
    """J05 · Inicio después de la tolerancia genera incidencia de retardo
    RF: RF-11/RF-15 (cumplimiento de horarios); parámetro tolerancia_retardo_min = 20 (entrevista P16)
    Tipo: válido (genera incidencia no crítica)
    Pre: hora 08:35
    Entrada: iniciar jornada dentro de la primera tienda
    Esperado: HTTP 201 e incidencia "Retardo" no crítica
    """
    a_las(8, 35)
    r = obs(_iniciar(_p1(app), esc))
    assert r.status_code == 201
    with app.app_context():
        inc = db.session.execute(db.select(Incidencia)).scalar_one()
        assert inc.tipo == "Retardo" and not inc.es_critica


def test_V01_checkin_independiente_del_inicio(app, esc, obs):
    """V01 · Check-in separado del inicio de jornada
    RF: RF-03 Check-in; reglas C3 y C4
    Tipo: válido
    Pre: P1 con jornada iniciada a las 08:05 y sin visitas
    Entrada: 08:10 check-in en Walmart a 15 m
    Esperado: iniciar jornada no crea visita; el check-in crea visita Abierta con su propia hora y ubicación
    """
    c = _p1(app)
    _iniciar(c, esc)
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 0
    a_las(8, 10)
    r = obs(_checkin(c, esc, metros=15))
    v = r.get_json()["visita"]
    assert r.status_code == 201 and v["estado"] == "Abierta"
    assert v["checkin"].endswith("08:10:00") and 14 < v["distancia_checkin_m"] < 16


def test_V02_checkin_requiere_jornada_y_geocerca(app, esc, obs):
    """V02 · Check-in sin jornada y fuera de la geocerca
    RF: RF-03 (dependencia RF-01); regla C4
    Tipo: inválido
    Pre: P1 sin jornada; después con jornada
    Entrada: (a) check-in sin jornada; (b) check-in a 80 m de Walmart
    Esperado: (a) 409 "Primero inicia tu jornada"; (b) 409 "No estás dentro del radio permitido"
    """
    c = _p1(app)
    r = _checkin(c, esc)
    assert r.status_code == 409 and "inicia tu jornada" in r.get_json()["error"]
    _iniciar(c, esc)
    r = obs(_checkin(c, esc, metros=80))
    assert r.status_code == 409 and "radio permitido" in r.get_json()["error"]


def test_V03_dos_visitas_abiertas(app, esc, obs):
    """V03 · Impedir dos visitas abiertas simultáneas y visita duplicada
    RF: RF-03; regla C9
    Tipo: inválido (estado incompatible)
    Pre: P1 con visita abierta en Walmart
    Entrada: check-in en Soriana (dentro de su geocerca) y repetir check-in en Walmart
    Esperado: HTTP 409 en ambos; solo existe una visita
    """
    c = _p1(app)
    _iniciar(c, esc)
    _checkin(c, esc)
    r = obs(_checkin(c, esc, idx=1, metros=5))
    assert r.status_code == 409 and "visita abierta" in r.get_json()["error"]
    assert _checkin(c, esc).status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 1


def test_E01_foto_valida_con_ubicacion_propia(app, esc, obs):
    """E01 · Fotografía válida vinculada a visita y categoría con ubicación propia
    RF: RF-05, RF-06, RNF-13; reglas D (fecha, hora, ubicación propia, validación guardada)
    Tipo: válido
    Pre: visita abierta en Walmart
    Entrada: foto JPEG "Anaquel antes" a 20 m de la tienda
    Esperado: HTTP 201; estatus Válida; se guardan hash SHA-256, distancia, coordenadas y hora propias
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    a_las(8, 20)
    r = obs(subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 20)))
    e = r.get_json()["evidencia"]
    assert r.status_code == 201 and e["estatus_validacion"] == "Válida" and e["dentro_geocerca"]
    assert len(e["hash_imagen"]) == 64 and 19 < e["distancia_m"] < 21 and e["fecha_hora_captura"].endswith("08:20:00")
    assert c.get(e["url"]).status_code == 200


def test_E02_foto_fuera_de_geocerca_no_cuenta(app, esc, obs):
    """E02 · Fotografía fuera de la geocerca se guarda pero no cuenta
    RF: RF-12 Validación automática; regla D (fuera de geocerca no completa la visita)
    Tipo: inválido (genera alerta)
    Pre: visita abierta en Walmart
    Entrada: foto "Precios" tomada a 300 m
    Esperado: HTTP 422; estatus "Fuera de geocerca"; incidencia crítica; la categoría Precios sigue faltando
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0], 300)))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Fuera de geocerca"
    assert "Precios" in r.get_json()["visita"]["categorias_faltantes"]
    with app.app_context():
        inc = db.session.execute(db.select(Incidencia).where(Incidencia.tipo == "Foto fuera de geocerca")).scalar_one()
        assert inc.es_critica


def test_E03_foto_repetida_rechazada(app, esc, obs):
    """E03 · La misma imagen enviada dos veces se rechaza
    RF: RF-12 (reutilización de fotografías); Hash_Imagen del diccionario
    Tipo: inválido (genera alerta)
    Pre: visita abierta; una foto ya aceptada
    Entrada: mismos bytes de imagen con otra categoría
    Esperado: HTTP 422, estatus Rechazada "foto repetida"
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    datos = foto()
    assert subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 5), datos=datos).status_code == 201
    r = obs(subir_foto(c, idv, "Anaquel después", punto(esc.coords[0], 5), datos=datos))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Rechazada"


def test_E04_archivo_no_imagen_y_categoria(app, esc, obs):
    """E04 · Archivo que no es imagen y categoría inexistente
    RF: RF-05/RF-06; RF-23
    Tipo: inválido
    Pre: visita abierta
    Entrada: (a) bytes de texto; (b) categoría "Selfie"
    Esperado: HTTP 400 en ambos y no se guarda evidencia
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0]), datos=b"esto no es una imagen"))
    assert r.status_code == 400
    assert subir_foto(c, idv, "Selfie", punto(esc.coords[0])).status_code == 400
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Evidencia)).scalar_one() == 0


def test_V04_checkout_bloqueado_por_categorias(app, esc, obs):
    """V04 · Check-out bloqueado si falta alguna categoría válida
    RF: RF-04 Check-out; regla D (servidor comprueba las 4 categorías y comunica faltantes)
    Tipo: inválido
    Pre: visita abierta con Anaquel antes y Anaquel después válidas, Precios fuera de geocerca
    Entrada: check-out dentro de la geocerca
    Esperado: HTTP 409 con faltantes = [Precios, Promociones]; visita sigue Abierta
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 5))
    subir_foto(c, idv, "Anaquel después", punto(esc.coords[0], 5))
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 400))
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)}))
    assert r.status_code == 409 and r.get_json()["faltantes"] == ["Precios", "Promociones"]


def test_V05_checkout_valido_no_cierra_jornada(app, esc, obs):
    """V05 · Check-out válido cierra la visita y mantiene la jornada abierta
    RF: RF-04; reglas C5, C6 y C7
    Tipo: válido
    Pre: visita abierta con las 4 categorías válidas (Promociones como exhibición sin promoción)
    Entrada: 09:45 check-out a 30 m (nueva ubicación)
    Esperado: HTTP 200; visita Cerrada con hora y coordenadas de salida propias; jornada sigue Abierta; estado En traslado
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    for cat in CATS[:3]:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    assert subir_foto(c, idv, "Promociones", punto(esc.coords[0], 5), sin_promocion=True).status_code == 201
    a_las(9, 45)
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 30)}))
    v = r.get_json()["visita"]
    assert r.status_code == 200 and v["estado"] == "Cerrada" and v["checkout"].endswith("09:45:00")
    assert 29 < v["distancia_checkout_m"] < 31
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["jornada"]["estado"] == "Abierta" and hoy["estado"]["estado_visita"] == "En traslado"


def test_V06_checkout_fuera_de_geocerca(app, esc, obs):
    """V06 · Check-out fuera de la geocerca
    RF: RF-04; regla C5
    Tipo: inválido
    Pre: visita con las 4 categorías válidas
    Entrada: check-out a 200 m
    Esperado: HTTP 409 "No estás dentro del radio permitido"; visita sigue Abierta
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    _cuatro_fotos(c, esc, idv)
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 200)}))
    assert r.status_code == 409 and "radio" in r.get_json()["error"]


def test_J06_finalizar_con_pendientes(app, esc, obs):
    """J06 · Cierre de jornada conforme a visitas pendientes
    RF: RF-01/RF-04; reglas C7, C8 y C9
    Tipo: inválido y válido con motivo
    Pre: P1 visitó Walmart; Soriana sigue pendiente
    Entrada: (a) finalizar con visita abierta; (b) finalizar sin motivo; (c) forzar con motivo
    Esperado: (a) 409 check-out pendiente; (b) 409 con pendientes [Soriana]; (c) 200 Finalizada + incidencia
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    fin = {**punto(esc.coords[0])}
    assert "check-out" in c.post("/api/promotor/jornada/finalizar", json=fin).get_json()["error"]
    _cuatro_fotos(c, esc, idv)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0])})
    r = c.post("/api/promotor/jornada/finalizar", json=fin)
    assert r.status_code == 409 and r.get_json()["pendientes"] == ["Soriana San Juan Bosco"]
    r = obs(c.post("/api/promotor/jornada/finalizar", json={**fin, "forzar": True,
                                                           "motivo": "La tienda Soriana cerró por inventario"}))
    assert r.status_code == 200 and r.get_json()["jornada"]["cierre_forzado"] is True
    with app.app_context():
        assert db.session.execute(db.select(Incidencia).where(
            Incidencia.tipo == "Jornada cerrada con tiendas pendientes")).scalar_one()


def test_J07_flujo_completo(app, esc, obs):
    """J07 · Flujo completo de la jornada con dos tiendas
    RF: RF-01, RF-03, RF-04, RF-05, RF-06, RF-07
    Tipo: válido (integración)
    Pre: P1 con Walmart y Soriana asignadas
    Entrada: iniciar, check-in, 4 fotos, check-out en cada tienda y finalizar sin forzar
    Esperado: jornada Finalizada sin cierre forzado; historial con 2 tiendas visitadas y 8 fotos
    """
    c = _p1(app)
    _iniciar(c, esc)
    # Corrección F03: el check-in de la primera tienda estaba a las 08:00,
    # antes del inicio de jornada (08:05), y el servidor lo rechazó con
    # razón. Ahora la primera visita empieza a las 08:10.
    for idx, h in ((0, 8), (1, 11)):
        a_las(h, 10)
        idv = _checkin(c, esc, idx=idx, metros=5).get_json()["visita"]["id_visita"]
        _cuatro_fotos(c, esc, idv, idx=idx)
        a_las(h + 1, 40)
        assert c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[idx])}).status_code == 200
    a_las(17, 0)
    r = obs(c.post("/api/promotor/jornada/finalizar", json=punto(esc.coords[1])))
    assert r.status_code == 200 and r.get_json()["jornada"]["cierre_forzado"] is False
    h = c.get("/api/promotor/historial?fecha=2026-11-04").get_json()["resumen"]
    assert h["tiendas_visitadas"] == 2 and h["fotos"] == 8 and h["minutos_en_tienda"] == 180


def test_P01_pausas_y_limites(app, esc, obs):
    """P01 · Pausas de comida y descanso con límite de cantidad
    RF: RF-08 Pausas programadas (1 comida de 60 min, 2 descansos de 20 min)
    Tipo: válido e inválido
    Pre: jornada abierta
    Entrada: comida; segunda comida; 2 descansos; tercer descanso
    Esperado: primera comida 201; segunda 409 "Ya has tomado tu pausa de comida hoy"; tercer descanso 409
    """
    c = _p1(app)
    _iniciar(c, esc)
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"}).status_code == 201
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 409  # una a la vez
    a_las(9, 0)
    c.post("/api/promotor/pausas/finalizar", json={})
    r = obs(c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"}))
    assert r.status_code == 409 and "comida" in r.get_json()["error"]
    for h in (10, 11):
        a_las(h, 0)
        assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 201
        a_las(h, 10)
        c.post("/api/promotor/pausas/finalizar", json={})
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 409


def test_P02_rastreo_suspendido_en_pausa_y_tras_cierre(app, esc, obs):
    """P02 · Suspensión del seguimiento durante pausas y después del cierre
    RF: RF-02, RF-08; Limitación 7 (no rastrea fuera de jornada ni en pausa)
    Tipo: inválido (el servidor rechaza puntos)
    Pre: jornada abierta
    Entrada: ubicación normal (09:00); pausa de descanso; ubicación en pausa; fin de pausa; cierre; ubicación tras cierre
    Esperado: 201, luego 409 "suspendido durante la pausa", y 409 tras finalizar; estado "Rastreo suspendido"
    """
    c = _p1(app)
    _iniciar(c, esc)
    a_las(9, 0)
    assert c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300)).status_code == 201
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"})
    a_las(9, 10)
    r = obs(c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300)))
    assert r.status_code == 409 and r.get_json()["codigo_rastreo"] == "en_pausa"
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["rastreo_activo"] is False and hoy["estado"]["estado_conexion"] == "Rastreo suspendido"
    a_las(9, 15)
    c.post("/api/promotor/pausas/finalizar", json={})
    c.post("/api/promotor/jornada/finalizar", json={**punto(esc.coords[0]), "forzar": True,
                                                   "motivo": "Prueba de rastreo tras el cierre"})
    a_las(9, 30)
    r = c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300))
    assert r.status_code == 409 and r.get_json()["codigo_rastreo"] == "sin_jornada"


def test_P03_checkin_y_foto_bloqueados_en_pausa(app, esc, obs):
    """P03 · No se registran check-in ni fotos durante una pausa
    RF: RF-08; regla C9 (estados incompatibles)
    Tipo: inválido
    Pre: jornada abierta con visita abierta y pausa de comida activa
    Entrada: subir foto y hacer check-out
    Esperado: HTTP 409 "Estás en pausa" en ambos
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"})
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0])))
    assert r.status_code == 409 and "pausa" in r.get_json()["error"]
    assert c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0])}).status_code == 409


def test_A01_promotor_no_accede_a_registros_ajenos(app, esc, obs):
    """A01 · Promotor sin acceso a registros ajenos
    RF: RNF-16 Seguridad de la información
    Tipo: no autorizado (petición manipulada)
    Pre: P1 con visita y foto; P3 es otro promotor
    Entrada: P3 consulta la visita de P1, su foto, usa una asignación de P1 y llama a la supervisión
    Esperado: 404 en visita, foto y asignación; 403 en endpoints de supervisión
    """
    c1 = _p1(app)
    _iniciar(c1, esc)
    asign = _asignaciones(c1)[1]["id_asignacion"]
    idv = _checkin(c1, esc).get_json()["visita"]["id_visita"]
    url = subir_foto(c1, idv, "Precios", punto(esc.coords[0])).get_json()["evidencia"]["url"]
    c3 = cliente(app, "p3@test.mx")
    assert c3.get(f"/api/promotor/visitas/{idv}").status_code == 404
    r = obs(c3.get(url))
    assert r.status_code == 404
    c3.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[2]))
    assert c3.post("/api/promotor/visitas/checkin", json={"id_asignacion": asign, **punto(esc.coords[1])}).status_code == 404
    assert c3.get("/api/supervision/mapa").status_code == 403
