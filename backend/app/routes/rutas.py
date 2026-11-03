"""Rutas y asignaciones (RF-09).

- Ruta: plantilla con tiendas en orden y días de la semana (portal admin).
- Asignación: tienda + fecha + orden para un promotor (lo que usa la
  jornada). Al cambiar un día, lo que se quita se marca Cancelada para
  conservar el historial. La asignación es manual: el ERS excluye la
  optimización automática de rutas (Limitación 6).
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.auth import error, puede_ver_promotor, roles_required, usuario_actual
from app.extensions import db
from app.models import Asignacion, Ruta, RutaTienda, Tienda, Usuario, Visita
from app.routes.tiendas import tienda_a_dict
from app.servicios import parametros
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("rutas", __name__, url_prefix="/api")

DIAS = ("LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM")


def _fecha(valor, campo="fecha"):
    try:
        return date.fromisoformat(str(valor)), None
    except (TypeError, ValueError):
        return None, f"La {campo} no es válida (usa AAAA-MM-DD)."


def _promotor_autorizado(id_promotor):
    yo = usuario_actual()
    try:
        id_promotor = int(id_promotor)
    except (TypeError, ValueError):
        return None, error("Selecciona un promotor.", 400)
    p = db.session.get(Usuario, id_promotor)
    if p is None or p.rol != "Promotor" or not puede_ver_promotor(yo, id_promotor):
        return None, error("Promotor no encontrado o fuera de tu alcance.", 404)
    return p, None


def _validar_tiendas(ids) -> tuple[list[Tienda], str | None]:
    if not isinstance(ids, list) or not ids:
        return [], "Agrega al menos una tienda."
    try:
        ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return [], "Lista de tiendas no válida."
    if len(set(ids)) != len(ids):
        return [], "Una tienda aparece repetida."
    tiendas = {t.id_tienda: t for t in db.session.execute(
        db.select(Tienda).where(Tienda.id_tienda.in_(ids))).scalars()}
    faltan = [i for i in ids if i not in tiendas]
    if faltan:
        return [], "Alguna tienda no existe."
    inactivas = [tiendas[i].nombre_comercial for i in ids if tiendas[i].estatus != "Activa"]
    if inactivas:
        return [], f"No se pueden asignar tiendas inactivas: {', '.join(inactivas)}."
    return [tiendas[i] for i in ids], None


def _advertencias(tiendas: list[Tienda]) -> list[str]:
    """Avisos que no bloquean. La entrevista menciona 3-4 tiendas diarias
    pero también tiendas de 5 horas, así que la cantidad no se impone."""
    avisos = []
    lo, hi = parametros.valor("tiendas_sugeridas_min"), parametros.valor("tiendas_sugeridas_max")
    if not lo <= len(tiendas) <= hi:
        avisos.append(f"Se sugieren de {lo} a {hi} tiendas por día; esta asignación tiene {len(tiendas)}. "
                      "Es válido si incluye tiendas de permanencia prolongada.")
    zonas = {t.zona for t in tiendas if t.zona}
    if len(zonas) > 1:
        avisos.append("Las tiendas pertenecen a zonas distintas (" + ", ".join(sorted(zonas)) +
                      "); esto puede incrementar los tiempos de traslado.")
    return avisos


# --------------------------------------------------------------- rutas

def ruta_a_dict(r: Ruta) -> dict:
    return {
        "id_ruta": r.id_ruta, "nombre_ruta": r.nombre_ruta, "id_promotor": r.id_promotor,
        "nombre_promotor": r.promotor.nombre_completo if r.promotor else None,
        "dias_programados": [d for d in r.dias_programados.split(",") if d],
        "estado": r.estado,
        "tiendas": [{"orden_visita": rt.orden_visita, **tienda_a_dict(rt.tienda)} for rt in r.tiendas],
    }


def _datos_ruta(datos):
    e = {}
    nombre = " ".join(str(datos.get("nombre_ruta") or "").split())
    if not nombre or len(nombre) > 100:
        e["nombre_ruta"] = "El nombre de la ruta es obligatorio (máximo 100 caracteres)."
    dias = datos.get("dias_programados") or []
    if not isinstance(dias, list) or not dias or any(d not in DIAS for d in dias):
        e["dias_programados"] = "Selecciona al menos un día de visita."
    dias = [d for d in DIAS if d in dias]
    tiendas, msg = _validar_tiendas(datos.get("tiendas"))
    if msg:
        e["tiendas"] = msg
    return nombre, dias, tiendas, e


@bp.get("/rutas")
@roles_required("Administrador", "Supervisor")
def listar_rutas():
    yo = usuario_actual()
    consulta = db.select(Ruta).join(Usuario, Ruta.id_promotor == Usuario.id_usuario)
    if yo.rol == "Supervisor":
        consulta = consulta.where(Usuario.id_supervisor == yo.id_usuario)
    q = (request.args.get("q") or "").strip()
    if q:
        p = f"%{q}%"
        consulta = consulta.where(or_(Ruta.nombre_ruta.ilike(p), Usuario.nombre_completo.ilike(p),
                                      Usuario.numero_empleado.ilike(p)))
    if request.args.get("id_promotor", "").isdigit():
        consulta = consulta.where(Ruta.id_promotor == int(request.args["id_promotor"]))
    if request.args.get("estado") in ("Activa", "Inactiva"):
        consulta = consulta.where(Ruta.estado == request.args["estado"])
    filas = db.session.execute(consulta.order_by(Ruta.nombre_ruta)).scalars().all()
    return jsonify(rutas=[ruta_a_dict(r) for r in filas], total=len(filas))


@bp.post("/rutas")
@roles_required("Administrador", "Supervisor")
def crear_ruta():
    datos = request.get_json(silent=True) or {}
    p, err = _promotor_autorizado(datos.get("id_promotor"))
    if err:
        return err
    if not p.esta_activo:
        return error("El promotor está inactivo.", 409)
    nombre, dias, tiendas, e = _datos_ruta(datos)
    if e:
        return error("Revisa los campos marcados.", 400, campos=e)
    r = Ruta(nombre_ruta=nombre, id_promotor=p.id_usuario, dias_programados=",".join(dias),
             estado="Activa", id_creado_por=usuario_actual().id_usuario, fecha_creacion=ahora())
    r.tiendas = [RutaTienda(id_tienda=t.id_tienda, orden_visita=i) for i, t in enumerate(tiendas, 1)]
    db.session.add(r)
    db.session.commit()
    return jsonify(mensaje="Ruta creada correctamente.", ruta=ruta_a_dict(r), advertencias=_advertencias(tiendas)), 201


def _ruta_autorizada(id_ruta):
    r = db.session.get(Ruta, id_ruta)
    if r is None or not puede_ver_promotor(usuario_actual(), r.id_promotor):
        return None, error("Ruta no encontrada.", 404)
    return r, None


@bp.put("/rutas/<int:id_ruta>")
@roles_required("Administrador", "Supervisor")
def editar_ruta(id_ruta):
    r, err = _ruta_autorizada(id_ruta)
    if err:
        return err
    datos = request.get_json(silent=True) or {}
    p, err = _promotor_autorizado(datos.get("id_promotor", r.id_promotor))
    if err:
        return err
    nombre, dias, tiendas, e = _datos_ruta(datos)
    if e:
        return error("Revisa los campos marcados.", 400, campos=e)
    r.nombre_ruta, r.id_promotor, r.dias_programados = nombre, p.id_usuario, ",".join(dias)
    r.tiendas.clear()
    db.session.flush()
    r.tiendas = [RutaTienda(id_tienda=t.id_tienda, orden_visita=i) for i, t in enumerate(tiendas, 1)]
    db.session.commit()
    return jsonify(mensaje="Ruta actualizada correctamente.", ruta=ruta_a_dict(r), advertencias=_advertencias(tiendas))


@bp.post("/rutas/<int:id_ruta>/<accion>")
@roles_required("Administrador", "Supervisor")
def estado_ruta(id_ruta, accion):
    if accion not in ("desactivar", "reactivar", "aplicar"):
        return error("Acción no válida.", 404)
    r, err = _ruta_autorizada(id_ruta)
    if err:
        return err
    if accion == "desactivar":
        r.estado = "Inactiva"
        db.session.commit()
        return jsonify(mensaje="Ruta desactivada. Las asignaciones ya creadas se conservan.", ruta=ruta_a_dict(r))
    if accion == "reactivar":
        r.estado = "Activa"
        db.session.commit()
        return jsonify(mensaje="Ruta reactivada.", ruta=ruta_a_dict(r))

    # aplicar: crea asignaciones por fecha a partir de la plantilla
    if r.estado != "Activa":
        return error("La ruta está inactiva.", 409)
    datos = request.get_json(silent=True) or {}
    desde, e1 = _fecha(datos.get("desde"), "fecha inicial")
    hasta, e2 = _fecha(datos.get("hasta"), "fecha final")
    if e1 or e2:
        return error(e1 or e2, 400)
    if desde < hoy():
        return error("No se pueden programar fechas pasadas.", 400)
    if hasta < desde or (hasta - desde).days > 62:
        return error("El rango debe ser de hasta 62 días y la fecha final no puede ser anterior.", 400)
    tiendas, msg = _validar_tiendas([rt.id_tienda for rt in r.tiendas])
    if msg:
        return error(msg, 409)
    creadas, omitidas = 0, []
    d = desde
    while d <= hasta:
        if DIAS[d.weekday()] in r.dias_programados.split(","):
            ya = db.session.execute(db.select(func.count()).select_from(Asignacion).where(
                Asignacion.id_promotor == r.id_promotor, Asignacion.fecha == d,
                Asignacion.estado == "Activa")).scalar_one()
            if ya:
                omitidas.append(d.isoformat())
            else:
                for i, t in enumerate(tiendas, 1):
                    db.session.add(Asignacion(
                        id_promotor=r.id_promotor, id_tienda=t.id_tienda, fecha=d, orden_visita=i,
                        estado="Activa", id_ruta=r.id_ruta, id_asignado_por=usuario_actual().id_usuario,
                        fecha_asignacion=ahora()))
                creadas += 1
        d += timedelta(days=1)
    db.session.commit()
    msg = f"Ruta aplicada a {creadas} día(s)."
    if omitidas:
        msg += f" Se omitieron {len(omitidas)} día(s) que ya tenían tiendas asignadas."
    return jsonify(mensaje=msg, dias_creados=creadas, dias_omitidos=omitidas)


# -------------------------------------------------------- asignaciones

def asignacion_a_dict(a: Asignacion, visita: Visita | None = None) -> dict:
    return {
        "id_asignacion": a.id_asignacion, "id_promotor": a.id_promotor, "fecha": a.fecha.isoformat(),
        "orden_visita": a.orden_visita, "estado": a.estado, "id_ruta": a.id_ruta,
        "fecha_asignacion": a.fecha_asignacion.isoformat(),
        "fecha_cancelacion": a.fecha_cancelacion.isoformat() if a.fecha_cancelacion else None,
        "motivo_cancelacion": a.motivo_cancelacion,
        "tienda": tienda_a_dict(a.tienda),
        "visita": None if visita is None else {
            "id_visita": visita.id_visita, "estado": visita.estado,
            "checkin": visita.fecha_hora_checkin.isoformat(),
            "checkout": visita.fecha_hora_checkout.isoformat() if visita.fecha_hora_checkout else None,
        },
    }


@bp.get("/asignaciones")
@roles_required("Administrador", "Supervisor")
def listar_asignaciones():
    p, err = _promotor_autorizado(request.args.get("id_promotor"))
    if err:
        return err
    desde, e1 = _fecha(request.args.get("desde") or request.args.get("fecha"))
    hasta, _ = _fecha(request.args.get("hasta") or request.args.get("fecha"))
    if e1:
        return error(e1, 400)
    hasta = hasta or desde
    consulta = db.select(Asignacion).where(
        Asignacion.id_promotor == p.id_usuario, Asignacion.fecha.between(desde, hasta))
    if request.args.get("historial") != "1":
        consulta = consulta.where(Asignacion.estado == "Activa")
    filas = db.session.execute(consulta.order_by(Asignacion.fecha, Asignacion.estado, Asignacion.orden_visita)).scalars().all()
    visitas = {v.id_asignacion: v for v in db.session.execute(db.select(Visita).where(
        Visita.id_asignacion.in_([a.id_asignacion for a in filas]))).scalars()} if filas else {}
    return jsonify(asignaciones=[asignacion_a_dict(a, visitas.get(a.id_asignacion)) for a in filas])


@bp.put("/asignaciones/dia")
@roles_required("Administrador", "Supervisor")
def guardar_dia():
    """Reemplaza el plan de un promotor para una fecha conservando historial."""
    datos = request.get_json(silent=True) or {}
    p, err = _promotor_autorizado(datos.get("id_promotor"))
    if err:
        return err
    if not p.esta_activo:
        return error("El promotor está inactivo.", 409)
    fecha, e = _fecha(datos.get("fecha"))
    if e:
        return error(e, 400)
    if fecha < hoy():
        return error("No se pueden modificar asignaciones de días pasados; se conservan como historial.", 409)
    ids = datos.get("tiendas") or []
    tiendas, msg = _validar_tiendas(ids) if ids else ([], None)
    if msg:
        return error(msg, 400)

    actuales = {a.id_tienda: a for a in db.session.execute(db.select(Asignacion).where(
        Asignacion.id_promotor == p.id_usuario, Asignacion.fecha == fecha,
        Asignacion.estado == "Activa")).scalars()}
    con_visita = set(db.session.execute(db.select(Visita.id_asignacion).where(
        Visita.id_asignacion.in_([a.id_asignacion for a in actuales.values()]))).scalars()) if actuales else set()
    nuevas_ids = [t.id_tienda for t in tiendas]

    for id_t, a in actuales.items():
        if id_t not in nuevas_ids:
            if a.id_asignacion in con_visita:
                return error(f"No se puede quitar {a.tienda.nombre_comercial}: ya tiene una visita registrada.", 409)
            a.estado = "Cancelada"
            a.fecha_cancelacion = ahora()
            a.motivo_cancelacion = str(datos.get("motivo") or "Modificación de la asignación")[:200]
    db.session.flush()
    yo = usuario_actual()
    for orden, t in enumerate(tiendas, 1):
        a = actuales.get(t.id_tienda)
        if a is not None:
            a.orden_visita = orden
        else:
            db.session.add(Asignacion(
                id_promotor=p.id_usuario, id_tienda=t.id_tienda, fecha=fecha, orden_visita=orden,
                estado="Activa", id_asignado_por=yo.id_usuario, fecha_asignacion=ahora()))
    db.session.commit()
    return jsonify(mensaje="Asignación guardada correctamente.", advertencias=_advertencias(tiendas) if tiendas else [])
