"""Parámetros globales: las reglas del sistema que el administrador puede ajustar."""
from flask import Blueprint, jsonify, request

from app.auth import error, roles_required
from app.extensions import db
from app.models import Parametro
from app.servicios import parametros as svc
from app.servicios.tiempo import ahora

bp = Blueprint("parametros", __name__, url_prefix="/api/parametros")


def _dict(p: Parametro) -> dict:
    # El nombre, la categoría y la explicación salen del código (no de la base)
    # para que se vean en lenguaje sencillo aunque la base se haya sembrado antes.
    nombre, _, _, rango, categoria = svc.DEFINICIONES.get(p.clave, (p.descripcion, None, None, p.rango, p.categoria))
    ayuda, unidad = svc.AYUDA.get(p.clave, ("", ""))
    return {
        "clave": p.clave, "descripcion": nombre, "ayuda": ayuda, "unidad": unidad, "tipo_dato": p.tipo_dato,
        "valor_activo": p.valor_activo, "valor_default": p.valor_default, "rango": rango,
        "categoria": categoria, "fecha_modificacion": p.fecha_modificacion.isoformat(),
    }


def _orden(d: dict):
    cats = svc.ORDEN_CATEGORIAS
    claves = list(svc.DEFINICIONES)
    return (cats.index(d["categoria"]) if d["categoria"] in cats else len(cats),
            claves.index(d["clave"]) if d["clave"] in claves else len(claves))


@bp.get("")
@roles_required("Administrador", "Supervisor", "Promotor")
def listar():
    svc.sembrar()
    q = (request.args.get("q") or "").strip().lower()
    filas = [_dict(p) for p in db.session.execute(db.select(Parametro)).scalars().all()
             if p.clave in svc.DEFINICIONES]
    if q:
        filas = [d for d in filas if q in d["descripcion"].lower() or q in d["ayuda"].lower()
                 or q in d["categoria"].lower()]
    return jsonify(parametros=sorted(filas, key=_orden))


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
    svc.olvidar_cache()
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
    svc.olvidar_cache()
    p.fecha_modificacion = ahora()
    db.session.commit()
    return jsonify(mensaje="Parámetro restablecido a su valor por defecto.", parametro=_dict(p))
