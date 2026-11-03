"""Parámetros globales (ERS 3.1, portal del administrador, punto 7)."""
from flask import Blueprint, jsonify, request

from app.auth import error, roles_required
from app.extensions import db
from app.models import Parametro
from app.servicios import parametros as svc
from app.servicios.tiempo import ahora

bp = Blueprint("parametros", __name__, url_prefix="/api/parametros")


def _dict(p: Parametro) -> dict:
    return {
        "clave": p.clave, "descripcion": p.descripcion, "tipo_dato": p.tipo_dato,
        "valor_activo": p.valor_activo, "valor_default": p.valor_default, "rango": p.rango,
        "categoria": p.categoria, "fecha_modificacion": p.fecha_modificacion.isoformat(),
    }


@bp.get("")
@roles_required("Administrador", "Supervisor", "Promotor")
def listar():
    svc.sembrar()
    q = (request.args.get("q") or "").strip().lower()
    filas = db.session.execute(db.select(Parametro).order_by(Parametro.categoria, Parametro.clave)).scalars().all()
    if q:
        filas = [p for p in filas if q in p.clave.lower() or q in p.descripcion.lower()]
    return jsonify(parametros=[_dict(p) for p in filas])


@bp.put("/<clave>")
@roles_required("Administrador")
def editar(clave):
    if clave not in svc.DEFINICIONES:
        return error("Parámetro no encontrado.", 404)
    svc.sembrar()
    datos = request.get_json(silent=True) or {}
    try:
        nuevo = svc.validar(clave, datos.get("valor", ""))
    except ValueError as e:
        return error(str(e), 400)
    p = db.session.execute(db.select(Parametro).where(Parametro.clave == clave)).scalar_one()
    p.valor_activo = nuevo
    p.fecha_modificacion = ahora()
    db.session.commit()
    return jsonify(mensaje="Parámetro actualizado.", parametro=_dict(p))


@bp.post("/<clave>/restablecer")
@roles_required("Administrador")
def restablecer(clave):
    if clave not in svc.DEFINICIONES:
        return error("Parámetro no encontrado.", 404)
    svc.sembrar()
    p = db.session.execute(db.select(Parametro).where(Parametro.clave == clave)).scalar_one()
    p.valor_activo = p.valor_default
    p.fecha_modificacion = ahora()
    db.session.commit()
    return jsonify(mensaje="Parámetro restablecido a su valor por defecto.", parametro=_dict(p))
