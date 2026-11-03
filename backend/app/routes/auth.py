from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth import (
    cerrar_sesion,
    error,
    iniciar_sesion,
    login_required,
    usuario_a_dict,
    usuario_actual,
)
from app.extensions import db
from app.models import Usuario
from app.servicios.tiempo import ahora

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."
PASSWORD_MIN = 8

# Hash de relleno: si el correo no existe se verifica igual una contraseña,
# para que el tiempo de respuesta no revele qué correos están registrados.
_hash_relleno: str | None = None


def _verificar_relleno(password: str) -> None:
    global _hash_relleno
    if _hash_relleno is None:
        _hash_relleno = generate_password_hash("relleno-no-valido")
    check_password_hash(_hash_relleno, password)


def _requiere_json():
    # Exigir JSON obliga al navegador a hacer una verificación previa (CORS)
    # en peticiones desde otros sitios, lo que bloquea envíos falsificados.
    if not request.is_json:
        return error("La petición debe enviarse como JSON.", 415)
    return None


def validar_password_nueva(password: str) -> str | None:
    if len(password) < PASSWORD_MIN:
        return f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres."
    if password.isdigit() or password.isalpha():
        return "La contraseña debe combinar letras y números."
    return None


@bp.post("/login")
def login():
    if (e := _requiere_json()):
        return e

    datos = request.get_json(silent=True) or {}
    correo = str(datos.get("correo") or "").strip().lower()
    password = str(datos.get("password") or "")

    if not correo or not password:
        return error("Escribe tu correo y tu contraseña.", 400)

    usuario = db.session.execute(
        db.select(Usuario).where(Usuario.correo_electronico == correo)
    ).scalar_one_or_none()

    if usuario is None:
        _verificar_relleno(password)
        return error(MENSAJE_CREDENCIALES, 401)

    if not usuario.check_password(password):
        # PENDIENTE: política de bloqueo por intentos fallidos. El ERS pide
        # bloquear tras 3 intentos, pero la duración no está definida. Por
        # ahora solo se registra el intento; no se bloquea la cuenta.
        usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
        usuario.ultimo_intento_fallido = ahora()
        db.session.commit()
        return error(MENSAJE_CREDENCIALES, 401)

    # El estatus se revisa después de la contraseña: solo quien conoce la
    # contraseña se entera de que la cuenta está inactiva.
    if not usuario.esta_activo:
        return error("Tu cuenta está inactiva. Contacta al administrador.", 403)

    if usuario.intentos_fallidos:
        usuario.intentos_fallidos = 0
        db.session.commit()

    iniciar_sesion(usuario)
    return jsonify(usuario=usuario_a_dict(usuario))


@bp.post("/logout")
def logout():
    if (e := _requiere_json()):
        return e
    cerrar_sesion()
    return jsonify(mensaje="Sesión cerrada.")


@bp.get("/me")
@login_required
def me():
    return jsonify(usuario=usuario_a_dict(usuario_actual()))


@bp.post("/cambiar-password")
@login_required
def cambiar_password():
    if (e := _requiere_json()):
        return e
    usuario = usuario_actual()
    datos = request.get_json(silent=True) or {}
    actual = str(datos.get("password_actual") or "")
    nueva = str(datos.get("password_nueva") or "")

    if not actual or not nueva:
        return error("Escribe tu contraseña actual y la nueva.", 400)
    if not usuario.check_password(actual):
        return error("La contraseña actual no es correcta.", 400)
    if (msg := validar_password_nueva(nueva)):
        return error(msg, 400)
    if actual == nueva:
        return error("La nueva contraseña debe ser distinta de la actual.", 400)

    usuario.set_password(nueva)
    usuario.debe_cambiar_password = False
    db.session.commit()
    # La huella de la sesión depende del hash: se renueva para no cerrar
    # la sesión de quien acaba de cambiarla.
    iniciar_sesion(usuario)
    return jsonify(mensaje="Contraseña actualizada correctamente.", usuario=usuario_a_dict(usuario))


@bp.post("/recuperar")
def recuperar():
    """Prototipo «¿Olvidaste tu contraseña?». El envío de enlaces por correo
    requiere un servidor SMTP que no está configurado; se informa cómo
    proceder sin revelar si el correo existe."""
    return jsonify(
        mensaje="Si el correo está registrado, pide al administrador que te asigne una contraseña temporal.",
        envio_correo="no_configurado",
    )
