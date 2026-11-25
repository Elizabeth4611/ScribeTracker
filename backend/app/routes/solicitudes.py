"""Solicitudes de ajuste (RF-15 del modelo de diseño, etapa 3).

El promotor pide un ajuste sobre un día (por ejemplo, "olvidé hacer
check-out" o "la tienda estaba cerrada") con un motivo; su supervisor la
aprueba o la rechaza con un comentario. Las aprobadas y rechazadas aparecen
en el reporte de desempeño. Cerrar la jornada con tiendas pendientes crea
automáticamente una solicitud "Tienda no visitada" por cada tienda.
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from app.auth import error, ids_promotores_visibles, puede_ver_promotor, roles_required, usuario_actual
from app.extensions import db
from app.models import Asignacion, SolicitudAjuste
from app.models.operacion import TIPOS_SOLICITUD
from app.servicios import operacion as op
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("solicitudes", __name__, url_prefix="/api")

MOTIVO_MIN, MOTIVO_MAX = 10, 300
DIAS_MAX = 7  # se puede pedir un ajuste de hoy y de los 7 días anteriores


def solicitud_a_dict(s: SolicitudAjuste) -> dict:
    t = s.asignacion.tienda if s.asignacion else None
    return {
        "id_solicitud": s.id_solicitud, "id_promotor": s.id_promotor,
        "nombre_promotor": s.promotor.nombre_completo if s.promotor else None,
        "fecha": s.fecha.isoformat(), "tipo": s.tipo, "motivo": s.motivo, "estado": s.estado,
        "id_asignacion": s.id_asignacion, "tienda": f"{t.nombre_comercial} {t.sucursal}" if t else None,
        "fecha_hora_solicitud": s.fecha_hora_solicitud.isoformat(),
        "revisor": s.revisor.nombre_completo if s.revisor else None,
        "fecha_hora_respuesta": s.fecha_hora_respuesta.isoformat() if s.fecha_hora_respuesta else None,
        "comentario_respuesta": s.comentario_respuesta,
    }


def crear(id_promotor: int, fecha: date, tipo: str, motivo: str, id_asignacion=None, id_jornada=None) -> SolicitudAjuste:
    """Valida y crea (sin commit). Lanza op.ReglaError."""
    if tipo not in TIPOS_SOLICITUD:
        raise op.ReglaError("Elige el tipo de ajuste: " + ", ".join(TIPOS_SOLICITUD) + ".", 400)
    motivo = " ".join(str(motivo or "").split())
    if not MOTIVO_MIN <= len(motivo) <= MOTIVO_MAX:
        raise op.ReglaError(f"Escribe el motivo (entre {MOTIVO_MIN} y {MOTIVO_MAX} caracteres).", 400)
    if fecha > hoy():
        raise op.ReglaError("No se puede pedir un ajuste de una fecha futura.", 400)
    if (hoy() - fecha).days > DIAS_MAX:
        raise op.ReglaError(f"Solo se pueden pedir ajustes de los últimos {DIAS_MAX} días.", 400)
    if id_asignacion is not None:
        a = db.session.get(Asignacion, id_asignacion)
        if a is None or a.id_promotor != id_promotor or a.fecha != fecha:
            raise op.ReglaError("La tienda indicada no está asignada para esa fecha.", 400)
    repetida = db.session.execute(db.select(SolicitudAjuste.id_solicitud).where(
        SolicitudAjuste.id_promotor == id_promotor, SolicitudAjuste.fecha == fecha,
        SolicitudAjuste.tipo == tipo, SolicitudAjuste.estado == "Pendiente",
        (SolicitudAjuste.id_asignacion == id_asignacion) if id_asignacion is not None
        else SolicitudAjuste.id_asignacion.is_(None))).first()
    if repetida:
        raise op.ReglaError("Ya tienes una solicitud pendiente igual. Espera la respuesta de tu supervisor.", 409)
    s = SolicitudAjuste(id_promotor=id_promotor, fecha=fecha, tipo=tipo, motivo=motivo,
                        id_asignacion=id_asignacion, id_jornada=id_jornada, estado="Pendiente",
                        fecha_hora_solicitud=ahora())
    db.session.add(s)
    return s


@bp.post("/promotor/solicitudes")
@roles_required("Promotor")
def solicitar():
    yo = usuario_actual()
    d = request.get_json(silent=True) or {}
    try:
        fecha = date.fromisoformat(str(d.get("fecha") or hoy().isoformat()))
    except ValueError:
        return error("Fecha no válida.", 400)
    id_asig = d.get("id_asignacion")
    try:
        id_asig = int(id_asig) if id_asig not in (None, "", "null") else None
    except (TypeError, ValueError):
        return error("Tienda no válida.", 400)
    j = op.jornada_de(yo.id_usuario, fecha)
    try:
        s = crear(yo.id_usuario, fecha, str(d.get("tipo") or ""), d.get("motivo"), id_asig,
                  j.id_jornada if j else None)
    except op.ReglaError as e:
        return error(e.mensaje, e.codigo)
    db.session.commit()
    return jsonify(mensaje="Solicitud enviada a tu supervisor.", solicitud=solicitud_a_dict(s)), 201


@bp.get("/promotor/solicitudes")
@roles_required("Promotor")
def mis_solicitudes():
    yo = usuario_actual()
    filas = db.session.execute(db.select(SolicitudAjuste).where(SolicitudAjuste.id_promotor == yo.id_usuario)
                               .order_by(SolicitudAjuste.fecha_hora_solicitud.desc()).limit(100)).scalars()
    return jsonify(solicitudes=[solicitud_a_dict(s) for s in filas])


@bp.get("/supervision/solicitudes")
@roles_required("Supervisor", "Administrador")
def listar():
    yo = usuario_actual()
    consulta = db.select(SolicitudAjuste).where(SolicitudAjuste.id_promotor.in_(ids_promotores_visibles(yo)))
    estado = request.args.get("estado")
    if estado in ("Pendiente", "Aprobada", "Rechazada"):
        consulta = consulta.where(SolicitudAjuste.estado == estado)
    filas = db.session.execute(consulta.order_by(SolicitudAjuste.fecha_hora_solicitud.desc()).limit(300)).scalars()
    return jsonify(solicitudes=[solicitud_a_dict(s) for s in filas])


@bp.put("/supervision/solicitudes/<int:id_solicitud>")
@roles_required("Supervisor", "Administrador")
def responder(id_solicitud):
    yo = usuario_actual()
    s = db.session.get(SolicitudAjuste, id_solicitud)
    if s is None or not puede_ver_promotor(yo, s.id_promotor):
        return error("Solicitud no encontrada.", 404)
    if s.estado != "Pendiente":
        return error(f"La solicitud ya fue respondida ({s.estado}).", 409)
    d = request.get_json(silent=True) or {}
    decision = d.get("decision")
    if decision not in ("Aprobada", "Rechazada"):
        return error("Indica si apruebas o rechazas la solicitud.", 400)
    comentario = " ".join(str(d.get("comentario") or "").split())[:300]
    if decision == "Rechazada" and len(comentario) < 5:
        return error("Escribe el motivo del rechazo para el promotor.", 400)
    s.estado, s.comentario_respuesta = decision, comentario or None
    s.id_revisor, s.fecha_hora_respuesta = yo.id_usuario, ahora()
    db.session.commit()
    return jsonify(mensaje=f"Solicitud {decision.lower()}.", solicitud=solicitud_a_dict(s))
