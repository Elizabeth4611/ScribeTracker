"""Suscripción a notificaciones push (RF-11, etapa 3)."""
from flask import Blueprint, current_app, jsonify, request

from app.auth import error, roles_required, usuario_actual
from app.extensions import db
from app.models import SuscripcionPush
from app.servicios import push
from app.servicios.tiempo import ahora

bp = Blueprint("notificaciones", __name__, url_prefix="/api/push")


@bp.get("/clave")
@roles_required("Supervisor", "Administrador")
def clave():
    return jsonify(clave_publica=push.clave_publica())


@bp.post("/suscribir")
@roles_required("Supervisor", "Administrador")
def suscribir():
    d = request.get_json(silent=True) or {}
    endpoint = str(d.get("endpoint") or "")
    claves = d.get("keys") or {}
    p256dh, auth = str(claves.get("p256dh") or ""), str(claves.get("auth") or "")
    if not endpoint.startswith("https://") or len(endpoint) > 500 or not p256dh or not auth:
        return error("Suscripción no válida.", 400)
    yo = usuario_actual()
    s = db.session.execute(db.select(SuscripcionPush).where(SuscripcionPush.endpoint == endpoint)).scalar_one_or_none()
    if s is None:
        s = SuscripcionPush(endpoint=endpoint, fecha_alta=ahora())
        db.session.add(s)
    s.id_usuario, s.clave_p256dh, s.clave_auth = yo.id_usuario, p256dh[:200], auth[:100]
    s.agente = (request.headers.get("User-Agent") or "")[:200]
    db.session.commit()
    return jsonify(mensaje="Notificaciones activadas en este navegador."), 201


@bp.post("/cancelar")
@roles_required("Supervisor", "Administrador")
def cancelar():
    d = request.get_json(silent=True) or {}
    s = db.session.execute(db.select(SuscripcionPush).where(
        SuscripcionPush.endpoint == str(d.get("endpoint") or ""),
        SuscripcionPush.id_usuario == usuario_actual().id_usuario)).scalar_one_or_none()
    if s is not None:
        db.session.delete(s)
        db.session.commit()
    return jsonify(mensaje="Notificaciones desactivadas en este navegador.")


@bp.post("/probar")
@roles_required("Supervisor", "Administrador")
def probar():
    yo = usuario_actual()
    n = db.session.execute(db.select(db.func.count()).select_from(SuscripcionPush).where(
        SuscripcionPush.id_usuario == yo.id_usuario)).scalar_one()
    if not n:
        return error("Primero activa las notificaciones en este navegador.", 409)
    push.encolar([yo.id_usuario], "ScribeTracker", "Notificación de prueba: las alertas críticas te llegarán así.",
                 "/panel/supervision")
    db.session.commit()
    return jsonify(mensaje="Notificación de prueba enviada.")
