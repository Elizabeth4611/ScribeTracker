"""API del promotor (vista móvil): jornada, visitas, pausas, seguimiento,
historial y perfil. Cada acción acepta el encabezado X-Id-Cliente para
que los reintentos y la sincronización sin conexión no dupliquen registros.
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.auth import error, idempotente, roles_required, usuario_actual
from app.extensions import db
from app.models import Asignacion, Evidencia, Incidencia, Jornada, Ruta, RutaTienda, Visita
from app.routes.tiendas import tienda_a_dict
from app.servicios import operacion as op
from app.servicios import parametros
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("promotor", __name__, url_prefix="/api/promotor")


def _regla(e: op.ReglaError):
    return error(e.mensaje, e.codigo, **e.extra)


def _datos():
    return request.get_json(silent=True) or {}


def evidencia_a_dict(e: Evidencia) -> dict:
    return {
        "id_evidencia": e.id_evidencia, "id_visita": e.id_visita, "categoria": e.categoria,
        "sin_promocion": bool(e.sin_promocion), "fecha_hora_captura": e.fecha_hora_captura.isoformat(),
        "fecha_hora_recepcion": e.fecha_hora_recepcion.isoformat(),
        "latitud": float(e.latitud), "longitud": float(e.longitud), "precision_m": e.precision_m,
        "distancia_m": e.distancia_m, "dentro_geocerca": bool(e.dentro_geocerca),
        "estatus_validacion": e.estatus_validacion, "motivo_validacion": e.motivo_validacion,
        "revision_supervisor": e.revision_supervisor, "comentario_revision": e.comentario_revision,
        "hash_imagen": e.hash_imagen, "origen": e.origen,
        "url": f"/api/evidencias/{e.id_evidencia}/imagen",
    }


def visita_a_dict(v: Visita) -> dict:
    duracion = None
    if v.fecha_hora_checkout:
        duracion = int((v.fecha_hora_checkout - v.fecha_hora_checkin).total_seconds() // 60)
    return {
        "id_visita": v.id_visita, "id_asignacion": v.id_asignacion, "estado": v.estado,
        "id_cliente": v.id_cliente, "tienda": tienda_a_dict(v.tienda),
        "checkin": v.fecha_hora_checkin.isoformat(), "distancia_checkin_m": v.distancia_checkin_m,
        "latitud_checkin": float(v.latitud_checkin), "longitud_checkin": float(v.longitud_checkin),
        "checkout": v.fecha_hora_checkout.isoformat() if v.fecha_hora_checkout else None,
        "distancia_checkout_m": v.distancia_checkout_m,
        "latitud_checkout": float(v.latitud_checkout) if v.latitud_checkout is not None else None,
        "longitud_checkout": float(v.longitud_checkout) if v.longitud_checkout is not None else None,
        "duracion_min": duracion, "origen": v.origen,
        "categorias_validas": sorted(op.categorias_validas(v)),
        "categorias_faltantes": op.categorias_faltantes(v),
        "evidencias": [evidencia_a_dict(e) for e in v.evidencias],
    }


def jornada_a_dict(j: Jornada | None) -> dict | None:
    if j is None:
        return None
    return {
        "id_jornada": j.id_jornada, "fecha": j.fecha.isoformat(), "estado": j.estado,
        "inicio": j.fecha_hora_inicio.isoformat(), "fin": j.fecha_hora_fin.isoformat() if j.fecha_hora_fin else None,
        "distancia_inicio_m": j.distancia_inicio_m, "cierre_forzado": bool(j.cierre_forzado),
        "motivo_cierre": j.motivo_cierre, "origen": j.origen,
        "pausas": [{
            "id_pausa": p.id_pausa, "tipo": p.tipo, "inicio": p.fecha_hora_inicio.isoformat(),
            "fin": p.fecha_hora_fin.isoformat() if p.fecha_hora_fin else None,
            "duracion_programada_min": p.duracion_programada_min,
            "duracion_real_min": int(((p.fecha_hora_fin or ahora()) - p.fecha_hora_inicio).total_seconds() // 60),
        } for p in j.pausas],
    }


def resumen_dia(id_promotor: int, fecha: date) -> dict:
    j = op.jornada_de(id_promotor, fecha)
    asignaciones = op.asignaciones_del_dia(id_promotor, fecha)
    visitas = {v.id_asignacion: v for v in db.session.execute(db.select(Visita).join(Asignacion).where(
        Visita.id_promotor == id_promotor, Asignacion.fecha == fecha)).scalars()}
    min_tienda = sum(int(((v.fecha_hora_checkout or ahora()) - v.fecha_hora_checkin).total_seconds() // 60)
                     for v in visitas.values())
    min_pausa = 0
    if j:
        min_pausa = sum(int(((p.fecha_hora_fin or ahora()) - p.fecha_hora_inicio).total_seconds() // 60)
                        for p in j.pausas)
    return {
        "fecha": fecha.isoformat(),
        "jornada": jornada_a_dict(j),
        "asignaciones": [{
            "id_asignacion": a.id_asignacion, "orden_visita": a.orden_visita, "tienda": tienda_a_dict(a.tienda),
            "visita": visita_a_dict(visitas[a.id_asignacion]) if a.id_asignacion in visitas else None,
        } for a in asignaciones],
        "resumen": {
            "tiendas_asignadas": len(asignaciones),
            "tiendas_visitadas": sum(1 for v in visitas.values() if v.estado == "Cerrada"),
            "minutos_en_tienda": min_tienda,
            "minutos_en_pausa": min_pausa,
            "fotos": sum(len(v.evidencias) for v in visitas.values()),
        },
    }


@bp.get("/hoy")
@roles_required("Promotor")
def hoy_promotor():
    yo = usuario_actual()
    fecha = hoy()
    datos = resumen_dia(yo.id_usuario, fecha)
    j = op.jornada_de(yo.id_usuario, fecha)
    datos["estado"] = op.estado_promotor(yo, fecha)
    datos["rastreo_activo"] = datos["estado"]["estado_jornada"] == "En jornada"
    datos["gps_intervalo_min"] = parametros.valor("gps_intervalo_min")
    datos["pausas_disponibles"] = {
        "Comida": parametros.valor("pausas_comida_max") - sum(1 for p in (j.pausas if j else []) if p.tipo == "Comida"),
        "Descanso": parametros.valor("pausas_descanso_max") - sum(1 for p in (j.pausas if j else []) if p.tipo == "Descanso"),
    }
    datos["hora_servidor"] = ahora().isoformat()
    return jsonify(datos)


@bp.post("/jornada/iniciar")
@roles_required("Promotor")
@idempotente("jornada_iniciar")
def iniciar_jornada():
    d = _datos()
    try:
        lat, lon, prec = op.leer_ubicacion(d)
        j = op.iniciar_jornada(usuario_actual(), lat, lon, prec, op.leer_captura(d))
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(mensaje="Jornada iniciada. El seguimiento de ubicación está activo.", jornada=jornada_a_dict(j)), 201


@bp.post("/jornada/finalizar")
@roles_required("Promotor")
@idempotente("jornada_finalizar")
def finalizar_jornada():
    d = _datos()
    try:
        lat, lon, prec = op.leer_ubicacion(d)
        j = op.finalizar_jornada(usuario_actual(), lat, lon, prec, op.leer_captura(d),
                                 forzar=bool(d.get("forzar")), motivo=d.get("motivo") or "")
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(mensaje="Jornada finalizada. El seguimiento de ubicación se detuvo.", jornada=jornada_a_dict(j))


@bp.post("/visitas/checkin")
@roles_required("Promotor")
@idempotente("checkin")
def checkin():
    d = _datos()
    try:
        lat, lon, prec = op.leer_ubicacion(d)
        v = op.checkin(usuario_actual(), d.get("id_asignacion"), lat, lon, prec, op.leer_captura(d),
                       id_cliente=(request.headers.get("X-Id-Cliente") or None))
    except op.ReglaError as e:
        return _regla(e)
    t = v.tienda
    return jsonify(mensaje=f"Check-in registrado correctamente en {t.nombre_comercial} {t.sucursal}.",
                   visita=visita_a_dict(v)), 201


@bp.post("/visitas/checkout")
@roles_required("Promotor")
@idempotente("checkout")
def checkout():
    d = _datos()
    yo = usuario_actual()
    try:
        v = op.buscar_visita(yo, d.get("id_visita"), d.get("visita_cliente"))
        lat, lon, prec = op.leer_ubicacion(d)
        v = op.checkout(yo, v, lat, lon, prec, op.leer_captura(d))
    except op.ReglaError as e:
        return _regla(e)
    minutos = int((v.fecha_hora_checkout - v.fecha_hora_checkin).total_seconds() // 60)
    return jsonify(mensaje=f"Check-out registrado. Tiempo en tienda: {minutos // 60} h {minutos % 60} min. "
                           "Tu jornada sigue abierta.", visita=visita_a_dict(v))


@bp.get("/visitas/<int:id_visita>")
@roles_required("Promotor")
def ver_visita(id_visita):
    try:
        v = op.buscar_visita(usuario_actual(), id_visita=id_visita)
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(visita=visita_a_dict(v))


@bp.post("/pausas/iniciar")
@roles_required("Promotor")
@idempotente("pausa_iniciar")
def iniciar_pausa():
    d = _datos()
    try:
        p = op.iniciar_pausa(usuario_actual(), d.get("tipo"), op.leer_captura(d))
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(mensaje=f"Pausa de {p.tipo.lower()} iniciada ({p.duracion_programada_min} min). "
                           "El seguimiento de ubicación está detenido.",
                   pausa={"id_pausa": p.id_pausa, "tipo": p.tipo, "inicio": p.fecha_hora_inicio.isoformat(),
                          "duracion_programada_min": p.duracion_programada_min}), 201


@bp.post("/pausas/finalizar")
@roles_required("Promotor")
@idempotente("pausa_finalizar")
def finalizar_pausa():
    d = _datos()
    try:
        p = op.finalizar_pausa(usuario_actual(), op.leer_captura(d))
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(mensaje="Pausa finalizada. Rastreo reactivado.",
                   pausa={"id_pausa": p.id_pausa, "tipo": p.tipo, "fin": p.fecha_hora_fin.isoformat()})


@bp.post("/ubicaciones")
@roles_required("Promotor")
@idempotente("ubicacion")
def ubicacion():
    d = _datos()
    try:
        lat, lon, prec = op.leer_ubicacion(d)
        u = op.registrar_ubicacion(usuario_actual(), lat, lon, prec, op.leer_captura(d),
                                   id_cliente=(request.headers.get("X-Id-Cliente") or None))
    except op.ReglaError as e:
        return _regla(e)
    return jsonify(mensaje="Ubicación registrada.", id_ubicacion=u.id_ubicacion), 201


@bp.get("/historial")
@roles_required("Promotor")
def historial():
    try:
        fecha = date.fromisoformat(request.args.get("fecha") or hoy().isoformat())
    except ValueError:
        return error("Fecha no válida.", 400)
    return jsonify(resumen_dia(usuario_actual().id_usuario, fecha))


@bp.get("/perfil")
@roles_required("Promotor")
def perfil():
    yo = usuario_actual()
    tiendas = db.session.execute(db.select(RutaTienda).join(Ruta).where(
        Ruta.id_promotor == yo.id_usuario, Ruta.estado == "Activa")).scalars().all()
    proximas = db.session.execute(db.select(Asignacion).where(
        Asignacion.id_promotor == yo.id_usuario, Asignacion.estado == "Activa",
        Asignacion.fecha.between(hoy(), hoy() + timedelta(days=7)))).scalars().all()
    vistas, lista = set(), []
    for t in [rt.tienda for rt in tiendas] + [a.tienda for a in proximas]:
        if t.id_tienda not in vistas:
            vistas.add(t.id_tienda)
            lista.append(f"{t.nombre_comercial} {t.sucursal}")
    return jsonify(tiendas_autorizadas=lista)


@bp.get("/notificaciones")
@roles_required("Promotor")
def notificaciones():
    """Avisos propios: incidencias que le afectan y validación de sus fotos."""
    yo = usuario_actual()
    desde = ahora() - timedelta(days=7)
    avisos = [{"tipo": i.tipo, "texto": i.descripcion, "fecha_hora": i.fecha_hora.isoformat(), "grupo": "Incidencia"}
              for i in db.session.execute(db.select(Incidencia).where(
                  Incidencia.id_promotor == yo.id_usuario, Incidencia.fecha_hora >= desde)
                  .order_by(Incidencia.fecha_hora.desc()).limit(30)).scalars()]
    for e in db.session.execute(db.select(Evidencia).join(Visita).where(
            Visita.id_promotor == yo.id_usuario, Evidencia.fecha_hora_recepcion >= desde)
            .order_by(Evidencia.fecha_hora_recepcion.desc()).limit(30)).scalars():
        texto = (f"Tu foto de {e.categoria.lower()} fue aceptada." if e.estatus_validacion == "Válida"
                 else f"Tu foto de {e.categoria.lower()} no cuenta: {e.motivo_validacion}")
        avisos.append({"tipo": "Foto", "texto": texto, "fecha_hora": e.fecha_hora_recepcion.isoformat(),
                       "grupo": "Foto validada"})
    avisos.sort(key=lambda x: x["fecha_hora"], reverse=True)
    return jsonify(notificaciones=avisos[:40])
