"""Generación, consulta y exportación de reportes."""
import json
from datetime import date

from flask import Blueprint, Response, jsonify, request

from app.auth import error, filtro_promotores, puede_ver_promotor, roles_required, usuario_actual
from app.extensions import db
from app.models import Reporte, Usuario
from app.servicios import reportes as svc
from app.servicios.tiempo import ahora

bp = Blueprint("reportes", __name__, url_prefix="/api/reportes")


def _dict(r: Reporte) -> dict:
    p = db.session.get(Usuario, r.id_promotor) if r.id_promotor else None
    g = db.session.get(Usuario, r.id_generado_por)
    return {"id_reporte": r.id_reporte, "tipo": r.tipo, "contenido": r.contenido,
            "fecha_generacion": r.fecha_generacion.isoformat(), "desde": r.fecha_inicio.isoformat(),
            "hasta": r.fecha_fin.isoformat(), "id_promotor": r.id_promotor,
            "promotor": p.nombre_completo if p else "Todos", "generado_por": g.nombre_completo if g else None,
            "formato": r.formato}


def _autorizado(r: Reporte) -> bool:
    yo = usuario_actual()
    if yo.rol == "Administrador":
        return True
    return r.id_generado_por == yo.id_usuario or (r.id_promotor and puede_ver_promotor(yo, r.id_promotor))


@bp.post("")
@roles_required("Supervisor", "Administrador")
def generar():
    yo = usuario_actual()
    d = request.get_json(silent=True) or {}
    tipo, contenido = d.get("tipo"), d.get("contenido", "Desempeño")
    if tipo not in ("Diario", "Semanal", "Mensual"):
        return error("Selecciona el tipo de reporte: diario, semanal o mensual.", 400)
    if contenido not in ("Desempeño", "Incidencias", "Exhibición"):
        return error("Contenido de reporte no válido.", 400)
    try:
        ref = date.fromisoformat(str(d.get("fecha")))
    except ValueError:
        return error("Selecciona una fecha válida.", 400)
    consulta = db.select(Usuario).where(filtro_promotores(yo))
    id_p = d.get("id_promotor")
    if id_p not in (None, "", "todos"):
        try:
            id_p = int(id_p)
        except (TypeError, ValueError):
            return error("Promotor no válido.", 400)
        if not puede_ver_promotor(yo, id_p):
            return error("Promotor no encontrado o fuera de tu alcance.", 404)
        consulta = consulta.where(Usuario.id_usuario == id_p)
    else:
        id_p = None
    promotores = db.session.execute(consulta.order_by(Usuario.nombre_completo)).scalars().all()
    m = svc.generar(tipo, contenido, ref, promotores)
    if not m["promotores"]:
        return error("No hay datos suficientes para generar el reporte.", 404)
    r = Reporte(tipo=tipo, contenido=contenido, fecha_generacion=ahora(), fecha_inicio=date.fromisoformat(m["desde"]),
                fecha_fin=date.fromisoformat(m["hasta"]), id_promotor=id_p, id_generado_por=yo.id_usuario,
                metricas=svc.a_json(m), formato="PDF")
    db.session.add(r)
    db.session.commit()
    return jsonify(mensaje="Reporte generado.", reporte=_dict(r), metricas=m), 201


@bp.get("")
@roles_required("Supervisor", "Administrador")
def listar():
    yo = usuario_actual()
    consulta = db.select(Reporte)
    if yo.rol == "Supervisor":
        consulta = consulta.where(Reporte.id_generado_por == yo.id_usuario)
    if request.args.get("id_promotor", "").isdigit():
        consulta = consulta.where(Reporte.id_promotor == int(request.args["id_promotor"]))
    filas = db.session.execute(consulta.order_by(Reporte.fecha_generacion.desc()).limit(200)).scalars()
    return jsonify(reportes=[_dict(r) for r in filas])


@bp.get("/<int:id_reporte>")
@roles_required("Supervisor", "Administrador")
def ver(id_reporte):
    r = db.session.get(Reporte, id_reporte)
    if r is None or not _autorizado(r):
        return error("Reporte no encontrado.", 404)
    return jsonify(reporte=_dict(r), metricas=json.loads(r.metricas))


@bp.get("/<int:id_reporte>/pdf")
@roles_required("Supervisor", "Administrador")
def exportar_pdf(id_reporte):
    r = db.session.get(Reporte, id_reporte)
    if r is None or not _autorizado(r):
        return error("Reporte no encontrado.", 404)
    try:
        contenido = svc.pdf(r, json.loads(r.metricas), usuario_actual().nombre_completo)
    except ImportError:
        return error("Falta la librería reportlab en el servidor (pip install -r requirements.txt).", 500)
    nombre = f"reporte_{r.contenido.lower()}_{r.tipo.lower()}_{r.fecha_inicio.isoformat()}_{r.id_reporte}.pdf"
    nombre = nombre.replace("ñ", "n").replace("ó", "o").replace("é", "e")
    return Response(contenido, mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"',
                             "Cache-Control": "no-store"})
