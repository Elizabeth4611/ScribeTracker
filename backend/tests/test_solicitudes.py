"""Etapa 3 · RF-15 del modelo de diseño: solicitudes de ajuste.

Caja negra. Particiones: tipo (4 válidos / otro), motivo (10-300 caracteres),
fecha (hoy a 7 días atrás / futura / más de 7 días), tienda (asignada ese
día / ajena), decisión del supervisor (Aprobada / Rechazada con comentario).
Valores límite: motivo de 9, 10, 300 y 301 caracteres; fecha de 7 y 8 días atrás.
"""
import pytest

from app.extensions import db
from app.models import SolicitudAjuste
from tests.conftest import cliente
from tests.escenario import iniciar_jornada, punto, subir_foto
from app.models.operacion import CATEGORIAS

MOTIVO = "La tienda Soriana estaba cerrada por inventario"


def _pedir(c, **d):
    return c.post("/api/promotor/solicitudes", json={"tipo": "Tienda no visitada", "motivo": MOTIVO, **d})


def _asig(c, idx=1):
    return c.get("/api/promotor/hoy").get_json()["asignaciones"][idx]["id_asignacion"]


# ---------------------------------------------------------------- promotor

def test_SOL01_solicitud_valida(app, esc, obs):
    c = cliente(app, "p1@test.mx")
    r = obs(_pedir(c, fecha="2026-11-04", id_asignacion=_asig(c)))
    assert r.status_code == 201 and r.get_json()["mensaje"] == "Solicitud enviada a tu supervisor."
    s = r.get_json()["solicitud"]
    assert s["estado"] == "Pendiente" and s["tienda"] == "Soriana San Juan Bosco"


@pytest.mark.parametrize("largo,codigo", [(9, 400), (10, 201), (300, 201), (301, 400)])
def test_SOL02_limites_del_motivo(app, esc, obs, largo, codigo):
    c = cliente(app, "p1@test.mx")
    r = obs(c.post("/api/promotor/solicitudes", json={"tipo": "Otro", "motivo": "x" * largo, "fecha": "2026-11-04"}))
    assert r.status_code == codigo


@pytest.mark.parametrize("fecha,codigo", [("2026-11-05", 400), ("2026-10-28", 201), ("2026-10-27", 400)])
def test_SOL03_limites_de_la_fecha(app, esc, obs, fecha, codigo):
    """Hoy es 4-nov: mañana es futura; 28-oct son 7 días (sí); 27-oct son 8 (no)."""
    c = cliente(app, "p1@test.mx")
    r = obs(c.post("/api/promotor/solicitudes", json={"tipo": "Corrección de horario", "motivo": MOTIVO, "fecha": fecha}))
    assert r.status_code == codigo


def test_SOL04_tipo_invalido(app, esc, obs):
    c = cliente(app, "p1@test.mx")
    r = obs(c.post("/api/promotor/solicitudes", json={"tipo": "Vacaciones", "motivo": MOTIVO}))
    assert r.status_code == 400 and r.get_json()["error"].startswith("Elige el tipo de ajuste")


def test_SOL05_tienda_de_otro_promotor(app, esc, obs):
    p3 = cliente(app, "p3@test.mx")
    ajena = _asig(p3, 0)
    r = obs(_pedir(cliente(app, "p1@test.mx"), id_asignacion=ajena))
    assert r.status_code == 400 and "no está asignada" in r.get_json()["error"]


def test_SOL06_no_duplicar_pendiente(app, esc, obs):
    c = cliente(app, "p1@test.mx")
    a = _asig(c)
    assert _pedir(c, id_asignacion=a).status_code == 201
    r = obs(_pedir(c, id_asignacion=a))
    assert r.status_code == 409


# -------------------------------------------------------------- supervisor

def _una(app):
    c = cliente(app, "p1@test.mx")
    return c, _pedir(c, id_asignacion=_asig(c)).get_json()["solicitud"]["id_solicitud"]


def test_SOL07_supervisor_aprueba(app, esc, obs):
    c, ids = _una(app)
    s1 = cliente(app, "s1@test.mx")
    assert [x["id_solicitud"] for x in s1.get("/api/supervision/solicitudes?estado=Pendiente").get_json()["solicitudes"]] == [ids]
    r = obs(s1.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Aprobada", "comentario": "Confirmado con la gerencia"}))
    assert r.status_code == 200 and r.get_json()["solicitud"]["estado"] == "Aprobada"
    mia = c.get("/api/promotor/solicitudes").get_json()["solicitudes"][0]
    assert mia["estado"] == "Aprobada" and mia["revisor"] == "Juan Supervisor"


def test_SOL08_rechazo_exige_comentario(app, esc, obs):
    _, ids = _una(app)
    s1 = cliente(app, "s1@test.mx")
    assert s1.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Rechazada"}).status_code == 400
    r = obs(s1.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Rechazada", "comentario": "La tienda sí abrió"}))
    assert r.status_code == 200 and r.get_json()["solicitud"]["estado"] == "Rechazada"


def test_SOL09_no_se_responde_dos_veces(app, esc, obs):
    _, ids = _una(app)
    s1 = cliente(app, "s1@test.mx")
    s1.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Aprobada"})
    r = obs(s1.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Rechazada", "comentario": "cambio de opinión"}))
    assert r.status_code == 409


def test_SOL10_permisos(app, esc, obs):
    c, ids = _una(app)
    assert cliente(app, "s2@test.mx").put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Aprobada"}).status_code == 404
    assert c.put(f"/api/supervision/solicitudes/{ids}", json={"decision": "Aprobada"}).status_code == 403
    assert cliente(app, "s2@test.mx").get("/api/supervision/solicitudes").get_json()["solicitudes"] == []


# ------------------------------------------------------------ integración

def test_SOL11_cierre_con_pendientes_crea_solicitud(app, esc, obs):
    """Antes (etapa 2) el cierre forzado quedaba sin aprobación; ahora genera la solicitud."""
    c = cliente(app, "p1@test.mx")
    iniciar_jornada(c, punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 10)}).get_json()["visita"]["id_visita"]
    for cat in CATEGORIAS:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    r = obs(c.post("/api/promotor/jornada/finalizar", json={**punto(esc.coords[0]), "forzar": True, "motivo": MOTIVO}))
    assert r.status_code == 200
    s = cliente(app, "s1@test.mx").get("/api/supervision/solicitudes").get_json()["solicitudes"]
    assert len(s) == 1 and s[0]["tipo"] == "Tienda no visitada" and s[0]["tienda"] == "Soriana San Juan Bosco"


def test_SOL12_reporte_de_desempeno_cuenta_aprobadas_y_rechazadas(app, esc, obs):
    c = cliente(app, "p1@test.mx")
    s1 = cliente(app, "s1@test.mx")
    a = _pedir(c, id_asignacion=_asig(c)).get_json()["solicitud"]["id_solicitud"]
    b = c.post("/api/promotor/solicitudes", json={"tipo": "Check-out olvidado", "motivo": MOTIVO}).get_json()["solicitud"]["id_solicitud"]
    c.post("/api/promotor/solicitudes", json={"tipo": "Otro", "motivo": MOTIVO})
    s1.put(f"/api/supervision/solicitudes/{a}", json={"decision": "Aprobada"})
    s1.put(f"/api/supervision/solicitudes/{b}", json={"decision": "Rechazada", "comentario": "No hay evidencia"})
    r = obs(s1.post("/api/reportes", json={"tipo": "Diario", "contenido": "Desempeño", "fecha": "2026-11-04",
                                          "id_promotor": esc.ids.p1}))
    m = r.get_json()["metricas"]["promotores"][0]
    assert (m["solicitudes_aprobadas"], m["solicitudes_rechazadas"], m["solicitudes_pendientes"]) == (1, 1, 1)
    pdf = s1.get(f"/api/reportes/{r.get_json()['reporte']['id_reporte']}/pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(SolicitudAjuste)).scalar_one() == 3
