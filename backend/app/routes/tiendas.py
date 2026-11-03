"""Catálogo de tiendas (RF-19, RF-20, RF-21)."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.auth import error, roles_required
from app.extensions import db
from app.models import Asignacion, Ruta, RutaTienda, Tienda, Visita
from app.servicios import parametros
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("tiendas", __name__, url_prefix="/api/tiendas")


def tienda_a_dict(t: Tienda) -> dict:
    return {
        "id_tienda": t.id_tienda, "nombre_comercial": t.nombre_comercial, "cadena": t.cadena,
        "sucursal": t.sucursal, "direccion_completa": t.direccion_completa, "zona": t.zona,
        "latitud": float(t.latitud), "longitud": float(t.longitud),
        "radio_geocerca_m": t.radio_geocerca_m, "tiempo_estimado_min": t.tiempo_estimado_min,
        "estatus": t.estatus,
    }


def _texto(datos, clave, maximo, obligatorio=True):
    v = " ".join(str(datos.get(clave) or "").split())
    if obligatorio and not v:
        return v, "Este campo es obligatorio."
    if len(v) > maximo:
        return v, f"Máximo {maximo} caracteres."
    return v, None


def _validar(datos: dict):
    c, e = {}, {}
    for clave, maximo, obl in (("nombre_comercial", 100, True), ("cadena", 50, True),
                               ("sucursal", 50, True), ("direccion_completa", 255, True),
                               ("zona", 50, False)):
        c[clave], msg = _texto(datos, clave, maximo, obl)
        if msg:
            e[clave] = msg
    c["zona"] = c["zona"] or None

    for clave, lo, hi in (("latitud", -90, 90), ("longitud", -180, 180)):
        crudo = str(datos.get(clave) if datos.get(clave) is not None else "").strip()
        if not crudo:
            e[clave] = "Las coordenadas GPS son obligatorias para el cálculo de la geocerca."
            continue
        try:
            n = Decimal(crudo)
        except InvalidOperation:
            e[clave] = "Coordenada no válida."
            continue
        if not lo <= n <= hi:
            e[clave] = f"Debe estar entre {lo} y {hi}."
        c[clave] = n.quantize(Decimal("0.00000001"))

    radio = datos.get("radio_geocerca_m")
    if radio in (None, ""):
        radio = parametros.valor("radio_geocerca_default_m")
    try:
        radio = int(radio)
        if not 10 <= radio <= 1000:
            raise ValueError
        c["radio_geocerca_m"] = radio
    except (TypeError, ValueError):
        e["radio_geocerca_m"] = "El radio debe ser un número entre 10 y 1000 metros."

    te = datos.get("tiempo_estimado_min")
    if te in (None, ""):
        c["tiempo_estimado_min"] = None
    else:
        try:
            te = int(te)
            if not 5 <= te <= 720:
                raise ValueError
            c["tiempo_estimado_min"] = te
        except (TypeError, ValueError):
            e["tiempo_estimado_min"] = "Tiempo estimado entre 5 y 720 minutos."
    return c, e


@bp.get("")
@roles_required("Administrador", "Supervisor")
def listar():
    q = (request.args.get("q") or "").strip()
    consulta = db.select(Tienda)
    if q:
        p = f"%{q}%"
        consulta = consulta.where(or_(Tienda.nombre_comercial.ilike(p), Tienda.cadena.ilike(p),
                                      Tienda.sucursal.ilike(p)))
    for campo, col in (("cadena", Tienda.cadena), ("zona", Tienda.zona)):
        if request.args.get(campo):
            consulta = consulta.where(col == request.args[campo])
    if request.args.get("estatus") in ("Activa", "Inactiva"):
        consulta = consulta.where(Tienda.estatus == request.args["estatus"])
    pagina = max(int(request.args.get("pagina", 1) or 1), 1)
    por_pagina = min(max(int(request.args.get("por_pagina", 10) or 10), 1), 500)
    total = db.session.execute(db.select(func.count()).select_from(consulta.subquery())).scalar_one()
    filas = db.session.execute(consulta.order_by(Tienda.nombre_comercial, Tienda.sucursal)
                               .offset((pagina - 1) * por_pagina).limit(por_pagina)).scalars()
    return jsonify(tiendas=[tienda_a_dict(t) for t in filas], total=total, pagina=pagina, por_pagina=por_pagina)


@bp.get("/opciones")
@roles_required("Administrador", "Supervisor")
def opciones():
    cadenas = db.session.execute(db.select(Tienda.cadena).distinct().order_by(Tienda.cadena)).scalars().all()
    zonas = db.session.execute(db.select(Tienda.zona).where(Tienda.zona.is_not(None)).distinct()
                               .order_by(Tienda.zona)).scalars().all()
    return jsonify(cadenas=cadenas, zonas=zonas, radio_default=parametros.valor("radio_geocerca_default_m"))


@bp.get("/<int:id_tienda>")
@roles_required("Administrador", "Supervisor")
def detalle(id_tienda):
    t = db.session.get(Tienda, id_tienda)
    if t is None:
        return error("Tienda no encontrada.", 404)
    return jsonify(tienda=tienda_a_dict(t))


@bp.post("")
@roles_required("Administrador")
def crear():
    c, e = _validar(request.get_json(silent=True) or {})
    if e:
        return error("Revisa los campos marcados.", 400, campos=e)
    dup = db.session.execute(db.select(Tienda.id_tienda).where(
        Tienda.nombre_comercial == c["nombre_comercial"], Tienda.sucursal == c["sucursal"])).first()
    if dup:
        return error("Ya existe una tienda con ese nombre y sucursal.", 409,
                     campos={"sucursal": "Tienda duplicada."})
    t = Tienda(**c, estatus="Activa", fecha_alta=ahora())
    db.session.add(t)
    db.session.commit()
    return jsonify(mensaje="Tienda registrada correctamente.", tienda=tienda_a_dict(t)), 201


@bp.put("/<int:id_tienda>")
@roles_required("Administrador")
def editar(id_tienda):
    t = db.session.get(Tienda, id_tienda)
    if t is None:
        return error("Tienda no encontrada.", 404)
    c, e = _validar(request.get_json(silent=True) or {})
    if e:
        return error("Revisa los campos marcados.", 400, campos=e)
    dup = db.session.execute(db.select(Tienda.id_tienda).where(
        Tienda.nombre_comercial == c["nombre_comercial"], Tienda.sucursal == c["sucursal"],
        Tienda.id_tienda != id_tienda)).first()
    if dup:
        return error("Ya existe una tienda con ese nombre y sucursal.", 409)
    # Las visitas ya registradas guardaron su propia distancia y resultado;
    # cambiar coordenadas o radio solo afecta validaciones futuras.
    for k, v in c.items():
        setattr(t, k, v)
    db.session.commit()
    return jsonify(mensaje="Tienda actualizada correctamente.", tienda=tienda_a_dict(t))


@bp.post("/<int:id_tienda>/desactivar")
@roles_required("Administrador")
def desactivar(id_tienda):
    t = db.session.get(Tienda, id_tienda)
    if t is None:
        return error("Tienda no encontrada.", 404)
    if t.estatus == "Inactiva":
        return error("La tienda ya está inactiva.", 409)
    # Modelo de diseño RF-21: no se desactiva si está en una ruta activa o
    # tiene visitas programadas pendientes.
    rutas = db.session.execute(db.select(Ruta.nombre_ruta).join(RutaTienda).where(
        RutaTienda.id_tienda == id_tienda, Ruta.estado == "Activa")).scalars().all()
    futuras = db.session.execute(db.select(func.count()).select_from(Asignacion).where(
        Asignacion.id_tienda == id_tienda, Asignacion.estado == "Activa", Asignacion.fecha >= hoy(),
        Asignacion.id_asignacion.not_in(db.select(Visita.id_asignacion)))).scalar_one()
    if rutas or futuras:
        return error("No se puede desactivar porque está asignada a una ruta activa o tiene visitas programadas.",
                     409, rutas=rutas, asignaciones_pendientes=futuras)
    t.estatus = "Inactiva"
    db.session.commit()
    return jsonify(mensaje="Tienda desactivada correctamente.", tienda=tienda_a_dict(t))


@bp.post("/<int:id_tienda>/reactivar")
@roles_required("Administrador")
def reactivar(id_tienda):
    t = db.session.get(Tienda, id_tienda)
    if t is None:
        return error("Tienda no encontrada.", 404)
    t.estatus = "Activa"
    db.session.commit()
    return jsonify(mensaje="Tienda reactivada.", tienda=tienda_a_dict(t))
