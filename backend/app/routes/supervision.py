"""Panel de supervisión (Supervisor y Administrador): mapa, seguimiento,
historial de ubicaciones, visitas y evidencias, e incidencias.
El supervisor solo ve a sus promotores; el administrador ve a todos."""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.auth import error, filtro_promotores, ids_promotores_visibles, puede_ver_promotor, roles_required, usuario_actual
from app.extensions import db
from app.models import Asignacion, Incidencia, Jornada, Parametro, Reporte, Ruta, Tienda, Ubicacion, Usuario, Visita
from app.routes.promotor import resumen_dia, visita_a_dict
from app.routes.tiendas import tienda_a_dict
from app.servicios import alertas, parametros
from app.servicios import operacion as op
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("supervision", __name__, url_prefix="/api")


def _fecha_arg(nombre="fecha", defecto=None):
    v = request.args.get(nombre)
    if not v:
        return defecto
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def _promotor_arg():
    yo = usuario_actual()
    try:
        idp = int(request.args.get("id_promotor") or 0)
    except ValueError:
        idp = 0
    p = db.session.get(Usuario, idp) if idp else None
    if p is None or p.rol != "Promotor" or not puede_ver_promotor(yo, idp):
        return None
    return p


def incidencia_a_dict(i: Incidencia) -> dict:
    return {
        "id_incidencia": i.id_incidencia, "id_promotor": i.id_promotor,
        "nombre_promotor": i.promotor.nombre_completo if i.promotor else None,
        "tipo": i.tipo, "es_critica": bool(i.es_critica), "fecha_hora": i.fecha_hora.isoformat(),
        "descripcion": i.descripcion, "estado": i.estado, "origen": i.origen,
        "id_visita": i.id_visita, "id_evidencia": i.id_evidencia,
        "comentario_revision": i.comentario_revision,
        "fecha_hora_revision": i.fecha_hora_revision.isoformat() if i.fecha_hora_revision else None,
    }


@bp.get("/supervision/promotores")
@roles_required("Supervisor", "Administrador")
def promotores():
    yo = usuario_actual()
    filas = db.session.execute(db.select(Usuario).where(filtro_promotores(yo))
                               .order_by(Usuario.estatus, Usuario.nombre_completo)).scalars()
    return jsonify(promotores=[{"id_usuario": u.id_usuario, "nombre_completo": u.nombre_completo,
                                "numero_empleado": u.numero_empleado, "estatus": u.estatus,
                                "tipo_contrato": u.tipo_contrato} for u in filas])


@bp.get("/supervision/mapa")
@roles_required("Supervisor", "Administrador")
def mapa():
    yo = usuario_actual()
    fecha = hoy()
    ids = ids_promotores_visibles(yo)
    alertas.evaluar(fecha, ids)
    filas = []
    resumen = {"En tienda": 0, "En traslado": 0, "En pausa": 0, "Sin jornada": 0, "Finalizada": 0,
               "Desconectados": 0}
    for p in db.session.execute(db.select(Usuario).where(Usuario.id_usuario.in_(ids), Usuario.estatus == "Activo")
                                .order_by(Usuario.nombre_completo)).scalars():
        est = op.estado_promotor(p, fecha)
        asign = op.asignaciones_del_dia(p.id_usuario, fecha)
        visitas = {v.id_asignacion: v for v in db.session.execute(db.select(Visita).where(
            Visita.id_asignacion.in_([a.id_asignacion for a in asign]))).scalars()} if asign else {}
        clave = est["estado_visita"] or est["estado_jornada"]
        resumen[clave] = resumen.get(clave, 0) + 1
        if est["estado_jornada"] == "En jornada" and est["estado_conexion"] in ("Desactualizada", "Sin ubicación"):
            resumen["Desconectados"] += 1
        filas.append({
            "id_usuario": p.id_usuario, "nombre_completo": p.nombre_completo, "numero_empleado": p.numero_empleado,
            **est,
            "tiendas": [{"orden_visita": a.orden_visita, **tienda_a_dict(a.tienda),
                         "visita_estado": visitas[a.id_asignacion].estado if a.id_asignacion in visitas else None}
                        for a in asign],
            "visitadas": sum(1 for v in visitas.values() if v.estado == "Cerrada"),
            "asignadas": len(asign),
            "pausas_hoy": len(op.jornada_de(p.id_usuario, fecha).pausas) if op.jornada_de(p.id_usuario, fecha) else 0,
        })
    criticas = db.session.execute(db.select(Incidencia).where(
        Incidencia.id_promotor.in_(ids), Incidencia.es_critica == True, Incidencia.estado == "Pendiente",
        Incidencia.fecha_hora >= ahora() - timedelta(days=1)).order_by(Incidencia.fecha_hora.desc()).limit(20)).scalars()
    return jsonify(fecha=fecha.isoformat(), hora_servidor=ahora().isoformat(), promotores=filas, resumen=resumen,
                   alertas=[incidencia_a_dict(i) for i in criticas],
                   ubicacion_reciente_min=parametros.valor("ubicacion_reciente_min"))


@bp.get("/supervision/seguimiento")
@roles_required("Supervisor", "Administrador")
def seguimiento():
    p = _promotor_arg()
    if p is None:
        return error("Promotor no encontrado o fuera de tu alcance.", 404)
    fecha = _fecha_arg(defecto=hoy())
    if fecha is None:
        return error("Fecha no válida.", 400)
    datos = resumen_dia(p.id_usuario, fecha)
    datos["promotor"] = {"id_usuario": p.id_usuario, "nombre_completo": p.nombre_completo,
                         "numero_empleado": p.numero_empleado, "tipo_contrato": p.tipo_contrato}
    datos["estado"] = op.estado_promotor(p, fecha) if fecha == hoy() else None
    j = op.jornada_de(p.id_usuario, fecha)
    datos["ubicaciones"] = [] if j is None else [
        {"latitud": float(u.latitud), "longitud": float(u.longitud), "precision_m": u.precision_m,
         "fecha_hora": u.fecha_hora_captura.isoformat(), "origen": u.origen}
        for u in db.session.execute(db.select(Ubicacion).where(Ubicacion.id_jornada == j.id_jornada)
                                    .order_by(Ubicacion.fecha_hora_captura)).scalars()]
    inicio = date(fecha.year, fecha.month, fecha.day)
    datos["incidencias"] = [incidencia_a_dict(i) for i in db.session.execute(db.select(Incidencia).where(
        Incidencia.id_promotor == p.id_usuario,
        Incidencia.fecha_hora >= inicio, Incidencia.fecha_hora < inicio + timedelta(days=1))
        .order_by(Incidencia.fecha_hora)).scalars()]
    rutas = db.session.execute(db.select(Ruta).where(Ruta.id_promotor == p.id_usuario, Ruta.estado == "Activa")).scalars()
    datos["rutas"] = [{"id_ruta": r.id_ruta, "nombre_ruta": r.nombre_ruta, "dias_programados": r.dias_programados}
                      for r in rutas]
    return jsonify(datos)


@bp.get("/supervision/visitas")
@roles_required("Supervisor", "Administrador")
def visitas():
    yo = usuario_actual()
    desde = _fecha_arg("desde", hoy())
    hasta = _fecha_arg("hasta", desde)
    if desde is None or hasta is None or hasta < desde or (hasta - desde).days > 62:
        return error("Rango de fechas no válido (máximo 62 días).", 400)
    consulta = db.select(Visita).join(Asignacion).where(Asignacion.fecha.between(desde, hasta))
    if request.args.get("id_promotor"):
        p = _promotor_arg()
        if p is None:
            return error("Promotor no encontrado o fuera de tu alcance.", 404)
        consulta = consulta.where(Visita.id_promotor == p.id_usuario)
    else:
        consulta = consulta.where(Visita.id_promotor.in_(ids_promotores_visibles(yo)))
    filas = db.session.execute(consulta.order_by(Visita.fecha_hora_checkin.desc()).limit(300)).scalars().all()
    return jsonify(visitas=[{**visita_a_dict(v), "nombre_promotor": v.promotor.nombre_completo} for v in filas])


@bp.get("/incidencias")
@roles_required("Supervisor", "Administrador")
def listar_incidencias():
    yo = usuario_actual()
    desde = _fecha_arg("desde", hoy() - timedelta(days=30))
    hasta = _fecha_arg("hasta", hoy())
    if desde is None or hasta is None:
        return error("Fecha no válida.", 400)
    consulta = db.select(Incidencia).where(Incidencia.fecha_hora >= desde,
                                           Incidencia.fecha_hora < hasta + timedelta(days=1))
    if request.args.get("id_promotor"):
        p = _promotor_arg()
        if p is None:
            return error("Promotor no encontrado o fuera de tu alcance.", 404)
        consulta = consulta.where(Incidencia.id_promotor == p.id_usuario)
    else:
        consulta = consulta.where(Incidencia.id_promotor.in_(ids_promotores_visibles(yo)))
    if request.args.get("estado") in ("Pendiente", "Revisada", "Sancionada"):
        consulta = consulta.where(Incidencia.estado == request.args["estado"])
    if request.args.get("tipo"):
        consulta = consulta.where(Incidencia.tipo == request.args["tipo"])
    if request.args.get("critica") == "1":
        consulta = consulta.where(Incidencia.es_critica == True)
    filas = db.session.execute(consulta.order_by(Incidencia.fecha_hora.desc()).limit(500)).scalars().all()
    return jsonify(incidencias=[incidencia_a_dict(i) for i in filas])


@bp.post("/incidencias")
@roles_required("Supervisor", "Administrador")
def crear_incidencia():
    """Incidencia reportada manualmente por el supervisor (OBJ-05)."""
    yo = usuario_actual()
    d = request.get_json(silent=True) or {}
    try:
        idp = int(d.get("id_promotor") or 0)
    except ValueError:
        idp = 0
    p = db.session.get(Usuario, idp) if idp else None
    if p is None or p.rol != "Promotor" or not puede_ver_promotor(yo, idp):
        return error("Promotor no encontrado o fuera de tu alcance.", 404)
    tipo = " ".join(str(d.get("tipo") or "").split())
    desc = " ".join(str(d.get("descripcion") or "").split())
    if not tipo or len(tipo) > 50:
        return error("Indica el tipo de incidencia (máximo 50 caracteres).", 400)
    if len(desc) < 5:
        return error("Describe la incidencia.", 400)
    i = Incidencia(id_promotor=idp, tipo=tipo, es_critica=bool(d.get("es_critica")), fecha_hora=ahora(),
                   descripcion=desc, estado="Pendiente", origen="Supervisor", id_reporto=yo.id_usuario)
    db.session.add(i)
    db.session.commit()
    return jsonify(mensaje="Incidencia registrada.", incidencia=incidencia_a_dict(i)), 201


@bp.put("/incidencias/<int:id_incidencia>")
@roles_required("Supervisor", "Administrador")
def revisar_incidencia(id_incidencia):
    yo = usuario_actual()
    i = db.session.get(Incidencia, id_incidencia)
    if i is None or not puede_ver_promotor(yo, i.id_promotor):
        return error("Incidencia no encontrada.", 404)
    d = request.get_json(silent=True) or {}
    if d.get("estado") not in ("Pendiente", "Revisada", "Sancionada"):
        return error("Estado no válido.", 400)
    i.estado = d["estado"]
    i.comentario_revision = (" ".join(str(d.get("comentario") or "").split())[:300] or None)
    i.id_revisor, i.fecha_hora_revision = yo.id_usuario, ahora()
    db.session.commit()
    return jsonify(mensaje="Incidencia actualizada.", incidencia=incidencia_a_dict(i))


@bp.get("/admin/resumen")
@roles_required("Administrador")
def resumen_admin():
    ids = ids_promotores_visibles(usuario_actual())
    alertas.evaluar(hoy(), ids)
    contar = lambda m, *c: db.session.execute(db.select(func.count()).select_from(m).where(*c)).scalar_one()  # noqa: E731
    actividad = []
    for j in db.session.execute(db.select(Jornada).order_by(Jornada.fecha_hora_recepcion.desc()).limit(5)).scalars():
        p = db.session.get(Usuario, j.id_promotor)
        actividad.append({"fecha_hora": j.fecha_hora_inicio.isoformat(),
                          "texto": f"{p.nombre_completo} inició jornada"})
    for v in db.session.execute(db.select(Visita).order_by(Visita.recepcion_checkin.desc()).limit(5)).scalars():
        actividad.append({"fecha_hora": v.fecha_hora_checkin.isoformat(),
                          "texto": f"{v.promotor.nombre_completo}: check-in en {v.tienda.nombre_comercial} {v.tienda.sucursal}"})
    actividad.sort(key=lambda x: x["fecha_hora"], reverse=True)
    criticas = db.session.execute(db.select(Incidencia).where(
        Incidencia.es_critica == True, Incidencia.estado == "Pendiente")
        .order_by(Incidencia.fecha_hora.desc()).limit(10)).scalars()
    return jsonify(
        usuarios={"total": contar(Usuario), "activos": contar(Usuario, Usuario.estatus == "Activo"),
                  "promotores": contar(Usuario, Usuario.rol == "Promotor", Usuario.estatus == "Activo"),
                  "supervisores": contar(Usuario, Usuario.rol == "Supervisor", Usuario.estatus == "Activo")},
        tiendas={"total": contar(Tienda), "activas": contar(Tienda, Tienda.estatus == "Activa")},
        rutas={"total": contar(Ruta), "activas": contar(Ruta, Ruta.estado == "Activa")},
        parametros=contar(Parametro) or len(parametros.DEFINICIONES),
        reportes=contar(Reporte),
        alertas=[incidencia_a_dict(i) for i in criticas],
        actividad=actividad[:8],
    )
