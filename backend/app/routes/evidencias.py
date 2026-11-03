"""Evidencias fotográficas (RF-05, RF-06, RF-12, RNF-13).

Cada foto se guarda vinculada a la visita y a su categoría con su propia
fecha, hora y ubicación, que se valida contra la geocerca de la tienda. El
resultado queda guardado. Una foto fuera de la geocerca o repetida no
cuenta para completar la visita.

Límites (documentados): la cámara integrada evita elegir archivos de la
galería desde la interfaz, pero un navegador no puede garantizar que la
imagen no provenga de una cámara virtual; el hash SHA-256 detecta fotos
repetidas, no imágenes generadas por IA.
"""
import hashlib
import json
import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file

from app.auth import error, idempotente, puede_ver_promotor, roles_required, usuario_actual
from app.extensions import db
from app.models import Evidencia
from app.models.operacion import CATEGORIAS
from app.routes.promotor import evidencia_a_dict, visita_a_dict
from app.servicios import operacion as op
from app.servicios.geo import distancia_m
from app.servicios.tiempo import ahora

bp = Blueprint("evidencias", __name__, url_prefix="/api")

FIRMAS = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"), b"\x89PNG\r\n\x1a\n": ("image/png", ".png")}


def _tipo_imagen(datos: bytes):
    for firma, tipo in FIRMAS.items():
        if datos.startswith(firma):
            return tipo
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return ("image/webp", ".webp")
    return None


@bp.post("/promotor/evidencias")
@roles_required("Promotor")
@idempotente("evidencia")
def subir():
    yo = usuario_actual()
    f = request.files.get("foto")
    form = request.form
    categoria = (form.get("categoria") or "").strip()
    if categoria not in CATEGORIAS:
        return error("Selecciona una categoría: " + ", ".join(CATEGORIAS) + ".", 400)
    if f is None:
        return error("No se recibió la fotografía.", 400)
    datos = f.read()
    if not datos:
        return error("La fotografía está vacía.", 400)
    if len(datos) > current_app.config["EVIDENCIA_MAX_BYTES"]:
        return error("La fotografía supera los 5 MB.", 413)
    tipo = _tipo_imagen(datos)
    if tipo is None:
        return error("El archivo no es una imagen JPEG, PNG o WEBP.", 400)
    sin_promo = str(form.get("sin_promocion") or "").lower() in ("1", "true", "si", "sí")
    if sin_promo and categoria != "Promociones":
        return error("La opción «sin promociones» solo aplica a la categoría Promociones.", 400)

    try:
        visita = op.buscar_visita(yo, form.get("id_visita"), form.get("visita_cliente"))
        lat, lon, prec = op.leer_ubicacion(form)
        captura = op.leer_captura(form)
        op._exigir_jornada_sin_pausa(yo, captura)
        if visita.estado != "Abierta":
            raise op.ReglaError("La visita ya está cerrada; no se pueden agregar fotos.")
        if captura < visita.fecha_hora_checkin:
            raise op.ReglaError("La foto se tomó antes del check-in de la visita.", 400)
    except op.ReglaError as e:
        return error(e.mensaje, e.codigo, **e.extra)

    sha = hashlib.sha256(datos).hexdigest()
    t = visita.tienda
    d = round(distancia_m(t.latitud, t.longitud, lat, lon), 1)
    dentro = d <= t.radio_geocerca_m
    repetida = db.session.execute(db.select(Evidencia.id_evidencia).where(
        Evidencia.hash_imagen == sha, Evidencia.estatus_validacion != "Rechazada")).first()
    if repetida:
        estatus, motivo = "Rechazada", "La imagen ya se había enviado antes (foto repetida)."
    elif not dentro:
        estatus, motivo = "Fuera de geocerca", f"Tomada a {int(d)} m de la tienda (radio {t.radio_geocerca_m} m)."
    else:
        estatus, motivo = "Válida", None

    # Archivo: nombre aleatorio, nunca el nombre enviado por el cliente.
    rel = os.path.join(captura.strftime("%Y"), captura.strftime("%m"), f"{uuid.uuid4().hex}{tipo[1]}")
    destino = os.path.join(current_app.config["EVIDENCIAS_DIR"], rel)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as fh:
        fh.write(datos)

    try:
        meta_cliente = json.loads(form.get("metadatos") or "{}")
        if not isinstance(meta_cliente, dict):
            meta_cliente = {}
    except ValueError:
        meta_cliente = {}
    meta = {k: meta_cliente.get(k) for k in ("fuente", "ancho", "alto", "agente", "fecha_dispositivo")}
    meta.update({"tipo": tipo[0], "bytes": len(datos), "sha256": sha})

    ev = Evidencia(
        id_visita=visita.id_visita, id_cliente=request.headers.get("X-Id-Cliente") or None,
        categoria=categoria, sin_promocion=sin_promo, ruta_imagen=rel.replace(os.sep, "/"),
        hash_imagen=sha, metadatos_imagen=json.dumps(meta, ensure_ascii=False),
        fecha_hora_captura=captura, fecha_hora_recepcion=ahora(), latitud=lat, longitud=lon,
        precision_m=prec, distancia_m=d, dentro_geocerca=dentro, estatus_validacion=estatus,
        motivo_validacion=motivo, origen=op.origen_peticion(),
    )
    db.session.add(ev)
    db.session.flush()
    if estatus != "Válida":
        op.registrar_incidencia(
            yo.id_usuario, "Foto repetida" if repetida else "Foto fuera de geocerca",
            f"{categoria} en {t.nombre_comercial} {t.sucursal}: {motivo}", critica=True,
            clave=f"foto:{ev.id_evidencia}", id_jornada=visita.id_jornada, id_visita=visita.id_visita,
            id_evidencia=ev.id_evidencia)
    db.session.commit()

    if estatus == "Válida":
        mensaje = f"Foto guardada correctamente ({categoria})."
        codigo = 201
    else:
        mensaje = f"La foto se guardó pero NO cuenta para la visita: {motivo}"
        codigo = 422
    return jsonify(mensaje=mensaje, evidencia=evidencia_a_dict(ev), visita=visita_a_dict(visita)), codigo


@bp.get("/evidencias/<int:id_evidencia>/imagen")
@roles_required("Promotor", "Supervisor", "Administrador")
def imagen(id_evidencia):
    ev = db.session.get(Evidencia, id_evidencia)
    if ev is None or not puede_ver_promotor(usuario_actual(), ev.visita.id_promotor):
        return error("Evidencia no encontrada.", 404)
    ruta = os.path.join(current_app.config["EVIDENCIAS_DIR"], ev.ruta_imagen)
    if not os.path.isfile(ruta):
        return error("El archivo de la evidencia no está disponible.", 404)
    resp = send_file(ruta, mimetype=json.loads(ev.metadatos_imagen).get("tipo") or "image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.put("/evidencias/<int:id_evidencia>/revision")
@roles_required("Supervisor", "Administrador")
def revisar(id_evidencia):
    """Revisión manual opcional del supervisor. Es informativa: no cambia
    la validación automática ni reabre visitas cerradas."""
    yo = usuario_actual()
    ev = db.session.get(Evidencia, id_evidencia)
    if ev is None or not puede_ver_promotor(yo, ev.visita.id_promotor):
        return error("Evidencia no encontrada.", 404)
    d = request.get_json(silent=True) or {}
    rev = d.get("revision")
    if rev not in ("Aprobada", "Observada", "Sin revisar"):
        return error("Revisión no válida.", 400)
    ev.revision_supervisor = rev
    ev.comentario_revision = (" ".join(str(d.get("comentario") or "").split()) or None)
    ev.id_revisor = yo.id_usuario
    db.session.commit()
    return jsonify(mensaje="Revisión guardada.", evidencia=evidencia_a_dict(ev))
