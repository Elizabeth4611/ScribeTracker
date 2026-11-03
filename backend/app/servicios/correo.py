"""Envío de credenciales por correo (RF-03 del apartado 3.6).

El envío es un paso aparte del alta: si el correo falla, la cuenta ya quedó
creada y el administrador puede generar otra contraseña temporal sin crear
un usuario duplicado. Sin servidor SMTP configurado en .env, el resultado
es "no_configurado" y la contraseña temporal se muestra una sola vez al
administrador para que la entregue por otro medio.
"""
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def correo_configurado() -> bool:
    return bool(current_app.config.get("MAIL_SERVER"))


def enviar_credenciales(destino: str, nombre: str, password_temporal: str) -> str:
    """Devuelve 'enviado', 'no_configurado' o 'fallido'."""
    if not correo_configurado():
        return "no_configurado"
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = "Tu acceso a ScribeTracker"
    msg["From"] = cfg.get("MAIL_FROM") or cfg.get("MAIL_USERNAME")
    msg["To"] = destino
    msg.set_content(
        f"Hola {nombre}:\n\n"
        "Se creó tu cuenta en ScribeTracker.\n"
        f"Usuario: {destino}\n"
        f"Contraseña temporal: {password_temporal}\n\n"
        "Al entrar por primera vez el sistema te pedirá cambiarla.\n"
    )
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], int(cfg.get("MAIL_PORT") or 587), timeout=15) as s:
            if cfg.get("MAIL_USE_TLS", True):
                s.starttls(context=ssl.create_default_context())
            if cfg.get("MAIL_USERNAME"):
                s.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD") or "")
            s.send_message(msg)
        return "enviado"
    except Exception:  # noqa: BLE001 - cualquier fallo de red/SMTP
        current_app.logger.exception("No se pudo enviar el correo de credenciales")
        return "fallido"
