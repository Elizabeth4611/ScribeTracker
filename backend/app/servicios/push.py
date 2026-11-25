"""Notificaciones push (Web Push) para alertas críticas · RF-11, etapa 3.

El modelo de diseño pide "WhatsApp o notificación push". Se implementa push:
WhatsApp exige una cuenta de empresa de Meta con número verificado.

- Claves VAPID: se generan la primera vez y se guardan en backend/instance/
  vapid_privada.pem (carpeta ignorada por Git; no se suben).
- Las notificaciones se encolan en la sesión de base de datos y se envían
  solo si la transacción se confirma (after_commit), en un hilo aparte para
  no hacer esperar al promotor.
- Si el servicio de push responde 404/410, la suscripción ya no existe y se borra.
"""
import base64
import json
import os
import threading

from flask import current_app
from sqlalchemy import event

from app.extensions import db

_CLAVE = "_push_pendientes"


def _ruta_privada():
    carpeta = current_app.config.get("VAPID_DIR") or current_app.instance_path
    return os.path.join(carpeta, "vapid_privada.pem")


def _vapid():
    from py_vapid import Vapid
    ruta = _ruta_privada()
    if not os.path.isfile(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        v = Vapid()
        v.generate_keys()
        v.save_key(ruta)
    return Vapid.from_file(ruta)


def clave_publica() -> str:
    """applicationServerKey para el navegador (base64url del punto sin comprimir)."""
    from cryptography.hazmat.primitives import serialization
    pub = _vapid().public_key.public_bytes(serialization.Encoding.X962,
                                           serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(pub).decode().rstrip("=")


def enviar_a(suscripcion: dict, carga: dict) -> int:
    """Envía una notificación. Devuelve el código HTTP del servicio de push."""
    from pywebpush import WebPushException, webpush
    _vapid()  # crea las claves si todavía no existen
    try:
        r = webpush(subscription_info=suscripcion, data=json.dumps(carga, ensure_ascii=False),
                    vapid_private_key=_ruta_privada(),
                    vapid_claims={"sub": current_app.config.get("PUSH_CONTACTO", "mailto:soporte@scribetracker.test")},
                    timeout=10)
        return r.status_code
    except WebPushException as e:
        return e.response.status_code if e.response is not None else 0
    except Exception:  # sin red, etc.: la alerta sigue visible en el panel
        return 0


def encolar(ids_usuarios, titulo: str, cuerpo: str, url: str = "/panel/incidencias") -> None:
    """Se enviará cuando la transacción actual se confirme."""
    if not current_app.config.get("PUSH_HABILITADO", True):
        return
    pend = db.session.info.setdefault(_CLAVE, [])
    pend.append(([i for i in ids_usuarios if i], {"titulo": titulo, "cuerpo": cuerpo, "url": url}))


def _enviar_pendientes(app, pendientes):
    from app.models import SuscripcionPush
    with app.app_context():
        for ids, carga in pendientes:
            subs = db.session.execute(db.select(SuscripcionPush).where(SuscripcionPush.id_usuario.in_(ids))).scalars().all()
            for s in subs:
                codigo = app.extensions["st_push_enviar"](
                    {"endpoint": s.endpoint, "keys": {"p256dh": s.clave_p256dh, "auth": s.clave_auth}}, carga)
                if codigo in (404, 410):
                    db.session.delete(s)
        db.session.commit()
        db.session.remove()


def iniciar(app):
    """Registra los eventos de la sesión. Las pruebas pueden reemplazar
    app.extensions['st_push_enviar'] y usar PUSH_SINCRONO."""
    app.extensions.setdefault("st_push_enviar", enviar_a)

    @event.listens_for(db.session, "after_commit")
    def _tras_confirmar(sesion):
        pendientes = sesion.info.pop(_CLAVE, None)
        if not pendientes:
            return
        from flask import current_app as ca
        real = ca._get_current_object()
        if real.config.get("PUSH_SINCRONO"):
            # Se ejecuta fuera de esta sesión para no anidar transacciones.
            hilo = threading.Thread(target=_enviar_pendientes, args=(real, pendientes))
            hilo.start()
            hilo.join()
        else:
            threading.Thread(target=_enviar_pendientes, args=(real, pendientes), daemon=True).start()

    @event.listens_for(db.session, "after_rollback")
    def _tras_deshacer(sesion):
        sesion.info.pop(_CLAVE, None)
