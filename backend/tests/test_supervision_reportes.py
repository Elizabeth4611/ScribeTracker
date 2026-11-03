"""Pruebas de idempotencia/sin conexión (RNF-08), supervisión (RF-10, RF-14),
alertas e incidencias (RF-11, RF-18) y reportes (RF-13, RF-15, RF-16)."""
import json
import uuid
from datetime import datetime

from app.extensions import db
from app.models import Evidencia, Incidencia, Jornada, Ubicacion, Visita
from tests.conftest import cliente
from tests.escenario import a_las, punto, subir_foto

CATS = ["Anaquel antes", "Anaquel después", "Precios", "Promociones"]


def _jornada_con_visita(app, esc, cerrar=True):
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    a_las(8, 10)
    idv = c.post("/api/promotor/visitas/checkin",
                 json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 5)}).get_json()["visita"]["id_visita"]
    for cat in CATS:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    if cerrar:
        a_las(9, 40)
        c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    return c, idv


def test_O01_reintento_sin_duplicados(app, esc, obs):
    """O01 · Reintentos con el mismo identificador no duplican registros
    RF: RNF-08/RNF-09 sincronización; regla C9 (sin duplicados)
    Tipo: válido (idempotencia)
    Pre: P1 con jornada iniciada
    Entrada: el mismo check-in y la misma foto enviados 3 veces con igual X-Id-Cliente
    Esperado: misma respuesta (201) marcada "repetido"; 1 visita y 1 evidencia en la base
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    cab = {"X-Id-Cliente": str(uuid.uuid4())}
    cuerpos = [c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"],
                                                             **punto(esc.coords[0], 5)}, headers=cab) for _ in range(3)]
    assert [r.status_code for r in cuerpos] == [201, 201, 201]
    assert cuerpos[2].get_json()["repetido"] is True
    idv = cuerpos[0].get_json()["visita"]["id_visita"]
    cab_f = {"X-Id-Cliente": str(uuid.uuid4())}
    datos = b"\xff\xd8\xff\xe0" + b"x" * 300
    rs = [subir_foto(c, idv, "Precios", punto(esc.coords[0], 5), datos=datos, cabeceras=cab_f) for _ in range(3)]
    obs(rs[-1])
    assert [r.status_code for r in rs] == [201, 201, 201]
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 1
        assert db.session.execute(db.select(db.func.count()).select_from(Evidencia)).scalar_one() == 1


def test_O02_sincronizacion_respeta_hora_de_captura(app, esc, obs):
    """O02 · Eventos sin conexión: se valida al sincronizar con la hora de captura
    RF: RNF-08 Funcionamiento sin conexión
    Tipo: válido
    Pre: P1 sin señal desde las 08:05; llegan los eventos a las 10:00
    Entrada: inicio 08:05, check-in 08:15 (X-Origen sin-conexion) y foto 08:20 que referencia el check-in por su ID de cliente
    Esperado: registros con hora de captura 08:05/08:15/08:20, recepción 10:00 y origen "Sin conexión"
    """
    c = cliente(app, "p1@test.mx")
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    a_las(10, 0)
    off = {"X-Origen": "sin-conexion"}
    r = c.post("/api/promotor/jornada/iniciar", json={**punto(esc.coords[0]), "capturado_en": "2026-11-04T08:05:00"},
               headers={**off, "X-Id-Cliente": str(uuid.uuid4())})
    assert r.status_code == 201
    id_ci = str(uuid.uuid4())
    r = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0]),
                                                      "capturado_en": "2026-11-04T08:15:00"},
               headers={**off, "X-Id-Cliente": id_ci})
    assert r.status_code == 201
    form_coord = punto(esc.coords[0])
    import io
    r = obs(c.post("/api/promotor/evidencias", data={
        "categoria": "Precios", "visita_cliente": id_ci, **{k: str(v) for k, v in form_coord.items()},
        "capturado_en": "2026-11-04T08:20:00", "foto": (io.BytesIO(b"\xff\xd8\xff" + b"z" * 50), "f.jpg")},
        content_type="multipart/form-data", headers={**off, "X-Id-Cliente": str(uuid.uuid4())}))
    assert r.status_code == 201
    with app.app_context():
        j = db.session.execute(db.select(Jornada)).scalar_one()
        v = db.session.execute(db.select(Visita)).scalar_one()
        e = db.session.execute(db.select(Evidencia)).scalar_one()
        assert j.fecha_hora_inicio == datetime(2026, 11, 4, 8, 5) and j.origen == "Sin conexión"
        assert v.fecha_hora_checkin == datetime(2026, 11, 4, 8, 15) and v.recepcion_checkin == datetime(2026, 11, 4, 10, 0)
        assert e.fecha_hora_captura == datetime(2026, 11, 4, 8, 20) and e.origen == "Sin conexión"


def test_O03_evento_offline_invalido_se_rechaza(app, esc, obs):
    """O03 · Un evento sin conexión que viola una regla se rechaza al sincronizar
    RF: RNF-08; regla "una visita pendiente no se presenta como validada"
    Tipo: inválido
    Pre: P1 sin jornada
    Entrada: (a) check-in sin conexión fuera de geocerca tras iniciar; (b) hora de captura en el futuro
    Esperado: (a) 409 radio permitido; (b) 400 "hora del dispositivo está adelantada"
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    r = obs(c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 500),
                                                          "capturado_en": "2026-11-04T08:06:00"},
                   headers={"X-Origen": "sin-conexion", "X-Id-Cliente": str(uuid.uuid4())}))
    assert r.status_code == 409
    r = c.post("/api/promotor/ubicaciones", json={**punto(esc.coords[0]), "capturado_en": "2026-11-04T09:30:00"})
    assert r.status_code == 400 and "adelantada" in r.get_json()["error"]


def test_O04_ubicacion_capturada_en_pausa_no_se_guarda(app, esc, obs):
    """O04 · Punto capturado durante una pausa que llega tarde por falta de señal
    RF: RF-02, RF-08, RNF-08
    Tipo: inválido
    Pre: pausa de descanso de 09:00 a 09:20 ya terminada
    Entrada: a las 09:30 llega una ubicación capturada a las 09:10
    Esperado: HTTP 409 "suspendido durante la pausa"; no se guarda
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a_las(9, 0)
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"})
    a_las(9, 20)
    c.post("/api/promotor/pausas/finalizar", json={})
    a_las(9, 30)
    r = obs(c.post("/api/promotor/ubicaciones", json={**punto(esc.coords[0], 200), "capturado_en": "2026-11-04T09:10:00"}))
    assert r.status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Ubicacion)).scalar_one() == 1  # solo el inicio


def test_S01_mapa_y_alcance_supervisor(app, esc, obs):
    """S01 · Mapa con última ubicación y estados separados, limitado al ámbito
    RF: RF-10 Mapa en tiempo real; RF-02; estados de cuenta, jornada, visita y conexión
    Tipo: válido / alcance
    Pre: P1 en tienda (visita abierta); P2 sin jornada; P3 pertenece a S2
    Entrada: S1 consulta /api/supervision/mapa; admin consulta el mismo
    Esperado: S1 ve P1 y P2 (no P3), P1 "En tienda" con ubicación reciente; admin ve a los 3
    """
    _jornada_con_visita(app, esc, cerrar=False)
    r = obs(cliente(app, "s1@test.mx").get("/api/supervision/mapa"))
    ps = {p["numero_empleado"]: p for p in r.get_json()["promotores"]}
    assert set(ps) == {"P1", "P2"}
    p1 = ps["P1"]
    assert (p1["estado_cuenta"], p1["estado_jornada"], p1["estado_visita"], p1["estado_conexion"]) == \
           ("Activo", "En jornada", "En tienda", "Reciente")
    assert p1["ultima_ubicacion"]["fecha_hora"].startswith("2026-11-04T08:05")
    assert ps["P2"]["estado_jornada"] == "Sin jornada"
    admin = cliente(app, "admin@test.mx").get("/api/supervision/mapa").get_json()
    # Corrección F04: los datos base de la etapa 1 incluyen a "Pedro
    # Promotor" (activo, sin número de empleado); el administrador también
    # lo ve. Se verifica que vea a todos los promotores activos.
    assert {p["nombre_completo"] for p in admin["promotores"]} == {
        "Marco Promotor", "Julieta Promotora", "Pablo Promotor", "Pedro Promotor"}


def test_S02_ubicacion_desactualizada(app, esc, obs):
    """S02 · Diferenciar ubicación reciente de desactualizada
    RF: RF-10; excepción del modelo de diseño (promotor sin señal se muestra como desconectado)
    Tipo: válido
    Pre: P1 inició a las 08:05 y no envía ubicaciones; parámetro ubicacion_reciente_min = 20
    Entrada: S1 consulta el mapa a las 08:20 y a las 08:40
    Esperado: 08:20 "Reciente"; 08:40 "Desactualizada" y cuenta como desconectado
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    s1 = cliente(app, "s1@test.mx")
    a_las(8, 20)
    # Corrección F05: la lista viene ordenada por nombre (Julieta antes que
    # Marco); se busca a P1 por su número en lugar de tomar la posición 0.
    p1 = [p for p in s1.get("/api/supervision/mapa").get_json()["promotores"] if p["numero_empleado"] == "P1"][0]
    assert p1["estado_conexion"] == "Reciente"
    a_las(8, 40)
    r = obs(s1.get("/api/supervision/mapa"))
    p1 = [p for p in r.get_json()["promotores"] if p["numero_empleado"] == "P1"][0]
    assert p1["estado_conexion"] == "Desactualizada" and r.get_json()["resumen"]["Desconectados"] == 1


def test_I01_alerta_sin_llegada(app, esc, obs):
    """I01 · Alerta crítica: no llegó a su primera tienda
    RF: RF-11 Alertas automáticas (30 min); canal: notificación interna del panel
    Tipo: válido (alerta)
    Pre: P1 tiene asignaciones y no inicia jornada; P3 tampoco (pertenece a S2)
    Entrada: S1 consulta el mapa a las 08:25 y a las 08:31
    Esperado: 08:25 sin alerta; 08:31 una alerta crítica para P1, sin duplicarse al volver a consultar
    """
    s1 = cliente(app, "s1@test.mx")
    a_las(8, 25)
    assert s1.get("/api/supervision/mapa").get_json()["alertas"] == []
    a_las(8, 31)
    s1.get("/api/supervision/mapa")
    r = obs(s1.get("/api/supervision/mapa"))
    al = r.get_json()["alertas"]
    assert len(al) == 1 and al[0]["tipo"] == "Sin llegada a primera tienda" and al[0]["nombre_promotor"] == "Marco Promotor"


def test_I02_inactividad_fuera_de_tienda_y_no_dentro(app, esc, obs):
    """I02 · Inactividad: alerta fuera de tienda, no dentro de una visita larga
    RF: RF-11 (2 horas sin moverse) con la observación de la entrevista (tiendas de 5 horas)
    Tipo: válido
    Pre: P1 con visita abierta 08:10-11:00 (sin moverse); luego fuera de tienda sin moverse 11:00-13:05
    Entrada: S1 consulta el mapa a las 11:00 (en tienda) y a las 13:05 (fuera de tienda)
    Esperado: sin alerta de inactividad durante la visita; alerta crítica "Inactividad" a las 13:05
    """
    c, idv = _jornada_con_visita(app, esc, cerrar=False)
    s1 = cliente(app, "s1@test.mx")
    for h in (9, 10, 11):
        a_las(h, 0)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 5))
    assert not [a for a in s1.get("/api/supervision/mapa").get_json()["alertas"] if a["tipo"] == "Inactividad"]
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    for h, m in ((11, 30), (12, 0), (12, 30), (13, 0)):
        a_las(h, m)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 400))
    a_las(13, 5)
    r = obs(s1.get("/api/supervision/mapa"))
    assert [a["tipo"] for a in r.get_json()["alertas"]].count("Inactividad") == 1


def test_I03_seguimiento_de_incidencias(app, esc, obs):
    """I03 · Historial de incidencias por promotor y seguimiento manual
    RF: RF-18 Ver historial de incidencias; diccionario INCIDENCIA (Pendiente/Revisada/Sancionada)
    Tipo: válido / alcance
    Pre: P1 con una foto fuera de geocerca (incidencia crítica)
    Entrada: S1 lista incidencias de P1 y la marca como Revisada; S2 intenta modificarla
    Esperado: S1 ve 1 incidencia y la actualiza (200); S2 recibe 404
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"],
                                                        **punto(esc.coords[0])}).get_json()["visita"]["id_visita"]
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 500))
    s1 = cliente(app, "s1@test.mx")
    lista = s1.get(f"/api/incidencias?id_promotor={esc.ids.p1}").get_json()["incidencias"]
    assert len(lista) == 1 and lista[0]["es_critica"]
    r = obs(s1.put(f"/api/incidencias/{lista[0]['id_incidencia']}", json={"estado": "Revisada", "comentario": "Se habló con el promotor"}))
    assert r.status_code == 200 and r.get_json()["incidencia"]["estado"] == "Revisada"
    assert cliente(app, "s2@test.mx").put(f"/api/incidencias/{lista[0]['id_incidencia']}",
                                          json={"estado": "Sancionada"}).status_code == 404


def test_S03_historial_ubicaciones_y_evidencias(app, esc, obs):
    """S03 · Historial de ubicaciones y consulta de visitas con evidencias
    RF: RF-14 Historial de ubicaciones; RF-07/2.2 revisión de evidencias
    Tipo: válido / alcance
    Pre: P1 con jornada, 2 ubicaciones adicionales y una visita cerrada con 4 fotos
    Entrada: S1 consulta seguimiento y visitas de P1; S2 consulta el seguimiento de P1
    Esperado: 3 puntos en orden cronológico; 1 visita con 4 evidencias válidas; S2 recibe 404
    """
    c, _ = _jornada_con_visita(app, esc)
    for h in (10, 11):
        a_las(h, 0)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[1], h * 10))
    s1 = cliente(app, "s1@test.mx")
    r = obs(s1.get(f"/api/supervision/seguimiento?id_promotor={esc.ids.p1}&fecha=2026-11-04"))
    horas = [u["fecha_hora"][11:16] for u in r.get_json()["ubicaciones"]]
    assert horas == ["08:05", "10:00", "11:00"]
    vs = s1.get(f"/api/supervision/visitas?id_promotor={esc.ids.p1}&desde=2026-11-04").get_json()["visitas"]
    assert len(vs) == 1 and len([e for e in vs[0]["evidencias"] if e["estatus_validacion"] == "Válida"]) == 4
    assert cliente(app, "s2@test.mx").get(f"/api/supervision/seguimiento?id_promotor={esc.ids.p1}").status_code == 404


def test_REP01_reporte_consistente_con_registros(app, esc, obs):
    """REP01 · Reporte diario de desempeño consistente con los registros
    RF: RF-13, RF-15 Reportes de desempeño
    Tipo: válido
    Pre: P1 con 2 asignadas, 1 visitada (08:10-09:40), 1 foto fuera de geocerca adicional; jornada iniciada 08:05
    Entrada: S1 genera reporte Diario de Desempeño para P1 el 4-nov-2026
    Esperado: asignadas 2, visitadas 1, cumplimiento 50 %, tiempo promedio 90 min, fotos válidas 4 de 5, incidencias 1 crítica
    """
    c, idv = _jornada_con_visita(app, esc, cerrar=False)
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 500))
    a_las(9, 40)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    r = obs(cliente(app, "s1@test.mx").post("/api/reportes", json={"tipo": "Diario", "contenido": "Desempeño",
                                                                    "fecha": "2026-11-04", "id_promotor": esc.ids.p1}))
    assert r.status_code == 201
    m = r.get_json()["metricas"]["promotores"][0]
    assert (m["tiendas_asignadas"], m["tiendas_visitadas"], m["cumplimiento_pct"]) == (2, 1, 50.0)
    assert m["tiempo_promedio_tienda_min"] == 90 and (m["fotos_validas"], m["fotos_total"]) == (4, 5)
    with app.app_context():
        assert m["incidencias_total"] == db.session.execute(db.select(db.func.count()).select_from(Incidencia).where(
            Incidencia.id_promotor == esc.ids.p1)).scalar_one() == 1


def test_REP02_pdf_y_permisos(app, esc, obs):
    """REP02 · Exportar reporte de exhibición a PDF con evidencias y permisos
    RF: RF-16 Exportar reportes (PDF); entrevista P26 (imágenes de anaquel, precios y promociones)
    Tipo: válido / no autorizado
    Pre: P1 con visita cerrada y 4 fotos (imágenes de prueba no decodificables)
    Entrada: S1 genera reporte Semanal de Exhibición y descarga el PDF; S2 intenta descargarlo; S1 pide reporte de P3
    Esperado: PDF válido (%PDF); S2 recibe 404; reporte de P3 → 404
    """
    _jornada_con_visita(app, esc)
    s1 = cliente(app, "s1@test.mx")
    r = s1.post("/api/reportes", json={"tipo": "Semanal", "contenido": "Exhibición", "fecha": "2026-11-04"})
    assert r.status_code == 201 and r.get_json()["metricas"]["desde"] == "2026-11-02"
    idr = r.get_json()["reporte"]["id_reporte"]
    pdf = s1.get(f"/api/reportes/{idr}/pdf")
    obs(r, extra=f"PDF: HTTP {pdf.status_code}, {len(pdf.data)} bytes, tipo {pdf.mimetype}")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF" and pdf.mimetype == "application/pdf"
    assert cliente(app, "s2@test.mx").get(f"/api/reportes/{idr}/pdf").status_code == 404
    assert s1.post("/api/reportes", json={"tipo": "Diario", "fecha": "2026-11-04",
                                          "id_promotor": esc.ids.p3}).status_code == 404


def test_REP03_sin_datos(app, esc, obs):
    """REP03 · Reporte sin datos en el periodo
    RF: RF-13 (excepción "No hay datos suficientes para generar el reporte")
    Tipo: inválido
    Pre: no hay registros en marzo de 2026
    Entrada: reporte Mensual con fecha 2026-03-15
    Esperado: HTTP 404 con el mensaje del modelo de diseño
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/reportes", json={"tipo": "Mensual", "fecha": "2026-03-15"}))
    assert r.status_code == 404 and r.get_json()["error"] == "No hay datos suficientes para generar el reporte."


def test_REP04_pdf_incluye_fotos_reales(app, esc, obs):
    """REP04 · El PDF de exhibición incrusta las fotografías válidas
    RF: RF-16; entrevista P26 (reportes con imágenes de exhibición, precios y promociones)
    Tipo: válido
    Pre: visita cerrada con 4 fotos JPEG reales generadas con Pillow
    Entrada: reporte Diario de Exhibición y descarga del PDF
    Esperado: PDF con 4 imágenes incrustadas (objetos /Image)
    """
    import io as _io

    import pytest
    PIL = pytest.importorskip("PIL.Image")

    def jpeg(color):
        b = _io.BytesIO()
        PIL.new("RGB", (64, 48), color).save(b, "JPEG")
        return b.getvalue()

    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin",
                 json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 5)}).get_json()["visita"]["id_visita"]
    for cat, color in zip(CATS, ("red", "green", "blue", "yellow")):
        assert subir_foto(c, idv, cat, punto(esc.coords[0], 5), datos=jpeg(color)).status_code == 201
    a_las(9, 0)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    s1 = cliente(app, "s1@test.mx")
    idr = s1.post("/api/reportes", json={"tipo": "Diario", "contenido": "Exhibición",
                                         "fecha": "2026-11-04"}).get_json()["reporte"]["id_reporte"]
    pdf = s1.get(f"/api/reportes/{idr}/pdf")
    imagenes = pdf.data.count(b"/Subtype /Image")
    obs(pdf, extra=f"{len(pdf.data)} bytes, {imagenes} imágenes incrustadas")
    assert pdf.status_code == 200 and imagenes == 4
