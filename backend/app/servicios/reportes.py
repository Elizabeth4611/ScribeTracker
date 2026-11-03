"""Reportes diarios, semanales y mensuales (RF-13, RF-15, RF-16, RF-17, RF-18).

Las métricas se calculan con los registros reales de la base y se guardan
en Reporte.Metricas (JSON) para que el PDF refleje lo que se generó en ese
momento.
"""
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
from io import BytesIO

from flask import current_app

from app.extensions import db
from app.models import Asignacion, Evidencia, Incidencia, Jornada, Usuario, Visita
from app.models.operacion import CATEGORIAS
from app.servicios import parametros


def rango(tipo: str, ref: date) -> tuple[date, date]:
    if tipo == "Diario":
        return ref, ref
    if tipo == "Semanal":
        ini = ref - timedelta(days=ref.weekday())
        return ini, ini + timedelta(days=6)
    ini = ref.replace(day=1)
    sig = (ini + timedelta(days=32)).replace(day=1)
    return ini, sig - timedelta(days=1)


def _min(a, b):
    return int((b - a).total_seconds() // 60)


def metricas_promotor(p: Usuario, ini: date, fin: date, con_evidencias: bool) -> dict:
    fin_dt = datetime(fin.year, fin.month, fin.day) + timedelta(days=1)
    ini_dt = datetime(ini.year, ini.month, ini.day)
    asign = db.session.execute(db.select(Asignacion).where(
        Asignacion.id_promotor == p.id_usuario, Asignacion.estado == "Activa",
        Asignacion.fecha.between(ini, fin))).scalars().all()
    visitas = db.session.execute(db.select(Visita).join(Asignacion).where(
        Visita.id_promotor == p.id_usuario, Asignacion.fecha.between(ini, fin))
        .order_by(Visita.fecha_hora_checkin)).scalars().all()
    jornadas = db.session.execute(db.select(Jornada).where(
        Jornada.id_promotor == p.id_usuario, Jornada.fecha.between(ini, fin))).scalars().all()
    incid = db.session.execute(db.select(Incidencia).where(
        Incidencia.id_promotor == p.id_usuario, Incidencia.fecha_hora >= ini_dt,
        Incidencia.fecha_hora < fin_dt).order_by(Incidencia.fecha_hora)).scalars().all()

    cerradas = [v for v in visitas if v.estado == "Cerrada"]
    durac = [_min(v.fecha_hora_checkin, v.fecha_hora_checkout) for v in cerradas]
    hs_h, hs_m = (int(x) for x in parametros.valor("hora_salida").split(":"))
    salidas_anticipadas = sum(1 for j in jornadas if j.fecha_hora_fin and
                              (j.fecha_hora_fin.hour, j.fecha_hora_fin.minute) < (hs_h, hs_m))
    pausas = [pa for j in jornadas for pa in j.pausas]
    fotos = [e for v in visitas for e in v.evidencias]
    retardos = sum(1 for i in incid if i.tipo == "Retardo")

    m = {
        "id_promotor": p.id_usuario, "nombre": p.nombre_completo, "numero_empleado": p.numero_empleado,
        "tiendas_asignadas": len(asign),
        "tiendas_visitadas": len(cerradas),
        "visitas_sin_cierre": len(visitas) - len(cerradas),
        "cumplimiento_pct": round(100 * len(cerradas) / len(asign), 1) if asign else None,
        "tiempo_promedio_tienda_min": round(sum(durac) / len(durac), 1) if durac else None,
        "jornadas": len(jornadas),
        "jornadas_puntuales": len(jornadas) - retardos,
        "retardos": retardos,
        "salidas_anticipadas": salidas_anticipadas,
        "jornadas_cierre_forzado": sum(1 for j in jornadas if j.cierre_forzado),
        "pausas": len(pausas),
        "minutos_pausa": sum(_min(pa.fecha_hora_inicio, pa.fecha_hora_fin) for pa in pausas if pa.fecha_hora_fin),
        "fotos_total": len(fotos),
        "fotos_validas": sum(1 for e in fotos if e.estatus_validacion == "Válida"),
        "fotos_fuera_geocerca": sum(1 for e in fotos if e.estatus_validacion == "Fuera de geocerca"),
        "fotos_rechazadas": sum(1 for e in fotos if e.estatus_validacion == "Rechazada"),
        "incidencias_total": len(incid),
        "incidencias_criticas": sum(1 for i in incid if i.es_critica),
        "incidencias_por_tipo": dict(Counter(i.tipo for i in incid)),
        # RF-15 menciona «solicitudes de ajuste», pero no hay especificación
        # de ese proceso en el ERS ni en el modelo de diseño.
        "solicitudes_ajuste": "Sin especificación en el ERS",
        "incidencias": [{"fecha_hora": i.fecha_hora.isoformat(), "tipo": i.tipo, "critica": bool(i.es_critica),
                         "descripcion": i.descripcion, "estado": i.estado} for i in incid],
        "visitas": [{
            "fecha": v.fecha_hora_checkin.date().isoformat(),
            "tienda": f"{v.tienda.nombre_comercial} {v.tienda.sucursal}",
            "checkin": v.fecha_hora_checkin.strftime("%H:%M"),
            "checkout": v.fecha_hora_checkout.strftime("%H:%M") if v.fecha_hora_checkout else None,
            "duracion_min": _min(v.fecha_hora_checkin, v.fecha_hora_checkout) if v.fecha_hora_checkout else None,
            "evidencias": ([{"id": e.id_evidencia, "categoria": e.categoria, "estatus": e.estatus_validacion,
                             "hora": e.fecha_hora_captura.strftime("%H:%M"), "sin_promocion": bool(e.sin_promocion)}
                            for e in v.evidencias] if con_evidencias else None),
        } for v in visitas],
    }
    return m


def generar(tipo: str, contenido: str, ref: date, promotores: list[Usuario]) -> dict:
    ini, fin = rango(tipo, ref)
    filas = [metricas_promotor(p, ini, fin, contenido == "Exhibición") for p in promotores]
    con_datos = [f for f in filas if f["tiendas_asignadas"] or f["visitas"] or f["incidencias_total"] or f["jornadas"]]
    total = {
        "promotores": len(con_datos),
        "tiendas_asignadas": sum(f["tiendas_asignadas"] for f in filas),
        "tiendas_visitadas": sum(f["tiendas_visitadas"] for f in filas),
        "incidencias": sum(f["incidencias_total"] for f in filas),
        "incidencias_criticas": sum(f["incidencias_criticas"] for f in filas),
        "fotos_validas": sum(f["fotos_validas"] for f in filas),
    }
    total["cumplimiento_pct"] = (round(100 * total["tiendas_visitadas"] / total["tiendas_asignadas"], 1)
                                 if total["tiendas_asignadas"] else None)
    return {"tipo": tipo, "contenido": contenido, "desde": ini.isoformat(), "hasta": fin.isoformat(),
            "totales": total, "promotores": con_datos}


# ------------------------------------------------------------------- PDF

def _imagen_segura(ruta, Image, ancho, alto):
    """Corrección F06: reportlab lee la imagen al construir el documento, así
    que un archivo dañado hacía fallar todo el PDF. Se verifica antes con
    Pillow (dependencia de reportlab) y se omite la imagen inválida."""
    if not ruta or not os.path.isfile(ruta):
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(ruta) as im:
            im.load()
        return Image(ruta, width=ancho, height=alto, kind="proportional")
    except Exception:  # noqa: BLE001 - archivo ausente, truncado o no decodificable
        return None


def pdf(reporte, metricas: dict, generado_por: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rojo = colors.HexColor("#E30613")
    est = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=est["Title"], textColor=rojo, fontSize=18)
    h2 = ParagraphStyle("h2", parent=est["Heading2"], textColor=colors.HexColor("#1f2937"))
    n = ParagraphStyle("n", parent=est["BodyText"], fontSize=9, leading=11)

    def tabla(datos, anchos=None):
        t = Table(datos, colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rojo), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        return t

    def v(x, suf=""):
        return "—" if x is None else f"{x}{suf}"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.4 * cm, bottomMargin=1.4 * cm,
                            title=f"Reporte {metricas['contenido']} {metricas['tipo']}")
    h = [Paragraph(f"ScribeTracker · Reporte de {metricas['contenido'].lower()}", h1),
         Paragraph(f"<b>Periodo:</b> {metricas['tipo']} del {metricas['desde']} al {metricas['hasta']} &nbsp; "
                   f"<b>Generado:</b> {reporte.fecha_generacion:%d/%m/%Y %H:%M} por {generado_por} &nbsp; "
                   f"<b>Folio:</b> {reporte.id_reporte}", n), Spacer(1, 8)]
    t = metricas["totales"]
    h.append(tabla([["Promotores", "Asignadas", "Visitadas", "Cumplimiento", "Incidencias", "Críticas", "Fotos válidas"],
                    [t["promotores"], t["tiendas_asignadas"], t["tiendas_visitadas"], v(t["cumplimiento_pct"], "%"),
                     t["incidencias"], t["incidencias_criticas"], t["fotos_validas"]]]))
    if not metricas["promotores"]:
        h.append(Spacer(1, 10))
        h.append(Paragraph("No hay datos para el periodo y filtros seleccionados.", n))

    for i, p in enumerate(metricas["promotores"]):
        if i and metricas["contenido"] == "Exhibición":
            h.append(PageBreak())
        h += [Spacer(1, 12), Paragraph(f"{p['nombre']} ({p['numero_empleado'] or 's/n'})", h2)]
        if metricas["contenido"] in ("Desempeño", "Exhibición"):
            h.append(tabla([
                ["Indicador", "Valor", "Indicador", "Valor"],
                ["Tiendas visitadas / asignadas", f"{p['tiendas_visitadas']} / {p['tiendas_asignadas']}",
                 "Cumplimiento", v(p["cumplimiento_pct"], "%")],
                ["Tiempo promedio en tienda", v(p["tiempo_promedio_tienda_min"], " min"), "Jornadas", p["jornadas"]],
                ["Llegadas puntuales", p["jornadas_puntuales"], "Retardos", p["retardos"]],
                ["Salidas antes de hora", p["salidas_anticipadas"], "Cierres con pendientes", p["jornadas_cierre_forzado"]],
                ["Pausas (min)", f"{p['pausas']} ({p['minutos_pausa']} min)", "Fotos válidas / total",
                 f"{p['fotos_validas']} / {p['fotos_total']}"],
                ["Fotos fuera de geocerca", p["fotos_fuera_geocerca"], "Fotos repetidas", p["fotos_rechazadas"]],
                ["Incidencias (críticas)", f"{p['incidencias_total']} ({p['incidencias_criticas']})",
                 "Solicitudes de ajuste", "Sin especificación"],
            ], [5 * cm, 3.5 * cm, 4.5 * cm, 3.5 * cm]))
        if p["visitas"] and metricas["contenido"] != "Incidencias":
            h.append(Spacer(1, 6))
            h.append(tabla([["Fecha", "Tienda", "Entrada", "Salida", "Minutos"]] +
                           [[x["fecha"], Paragraph(x["tienda"], n), x["checkin"], v(x["checkout"]), v(x["duracion_min"])]
                            for x in p["visitas"]], [2.3 * cm, 7.5 * cm, 2 * cm, 2 * cm, 2 * cm]))
        if metricas["contenido"] in ("Incidencias", "Desempeño") and p["incidencias"]:
            h.append(Spacer(1, 6))
            h.append(tabla([["Fecha y hora", "Tipo", "Crítica", "Estado", "Descripción"]] +
                           [[x["fecha_hora"].replace("T", " ")[:16], Paragraph(x["tipo"], n), "Sí" if x["critica"] else "No",
                             x["estado"], Paragraph(x["descripcion"] or "", n)] for x in p["incidencias"]],
                           [3 * cm, 3.5 * cm, 1.4 * cm, 2 * cm, 7 * cm]))
        if metricas["contenido"] == "Exhibición":
            base = current_app.config["EVIDENCIAS_DIR"]
            for x in p["visitas"]:
                fotos = [e for e in (x["evidencias"] or []) if e["estatus"] == "Válida"]
                if not fotos:
                    continue
                h += [Spacer(1, 6), Paragraph(f"<b>{x['tienda']}</b> · {x['fecha']} {x['checkin']}–{v(x['checkout'])}", n)]
                celdas = []
                for e in sorted(fotos, key=lambda e: CATEGORIAS.index(e["categoria"])):
                    ev = db.session.get(Evidencia, e["id"])
                    ruta = os.path.join(base, ev.ruta_imagen) if ev else None
                    img = _imagen_segura(ruta, Image, 4 * cm, 3 * cm) or Paragraph("(imagen no disponible)", n)
                    rotulo = e["categoria"] + (" (exhibición, sin promoción)" if e["sin_promocion"] else "")
                    celdas.append([img, Paragraph(f"{rotulo}<br/>{e['hora']}", n)])
                fila_img = [c[0] for c in celdas]
                fila_txt = [c[1] for c in celdas]
                tt = Table([fila_img, fila_txt], colWidths=[4.3 * cm] * len(celdas))
                tt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 7)]))
                h.append(tt)

    doc.build(h)
    return buf.getvalue()


def a_json(m: dict) -> str:
    return json.dumps(m, ensure_ascii=False)
