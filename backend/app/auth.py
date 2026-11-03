"""Utilidades de autenticación, autorización y alcance por rol.

La sesión se guarda en la cookie firmada de Flask (HttpOnly). En cada
petición protegida se vuelve a leer el usuario de la base de datos, de modo
que si un administrador lo marca como Inactivo, cambia su rol o su
contraseña, la sesión deja de servir de inmediato.
"""
import hashlib
import hmac
import json
import re
from functools import wraps

from flask import current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import EventoCliente, Usuario
from app.servicios.tiempo import ahora

SESSION_USER_KEY = "id_usuario"
SESSION_FP_KEY = "huella"
UUID_RE = re.compile(r"^[0-9a-fA-F-]{8,36}$")


def error(mensaje: str, http: int = 400, **extra):
    # Corrección F02: el segundo parámetro se llamaba "codigo" y chocaba con
    # el dato extra codigo="cambiar_password" (TypeError en tiempo de ejecución).
    return jsonify(error=mensaje, **extra), http


def _huella_password(usuario: Usuario) -> str:
    """HMAC del hash de contraseña: si la contraseña cambia, la sesión
    deja de ser válida. No se guarda el hash en la cookie."""
    clave = current_app.config["SECRET_KEY"].encode()
    return hmac.new(clave, usuario.password_hash.encode(), hashlib.sha256).hexdigest()


def iniciar_sesion(usuario: Usuario) -> None:
    session.clear()
    session[SESSION_USER_KEY] = usuario.id_usuario
    session[SESSION_FP_KEY] = _huella_password(usuario)


def cerrar_sesion() -> None:
    session.clear()


def usuario_actual() -> Usuario | None:
    """Devuelve el usuario de la sesión si sigue siendo válido."""
    usuario = None
    id_usuario = session.get(SESSION_USER_KEY)
    if id_usuario is not None:
        candidato = db.session.get(Usuario, id_usuario)
        if (
            candidato is not None
            and candidato.esta_activo
            and hmac.compare_digest(session.get(SESSION_FP_KEY, ""), _huella_password(candidato))
        ):
            usuario = candidato
        else:
            session.clear()
    return usuario


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            return error("No has iniciado sesión.", 401)
        return vista(*args, **kwargs)

    return envoltura


def roles_required(*roles: str):
    """Solo usuarios activos con alguno de estos roles. Quien tiene una
    contraseña temporal debe cambiarla antes de usar el sistema."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if usuario is None:
                return error("No has iniciado sesión.", 401)
            if usuario.debe_cambiar_password:
                return error("Debes cambiar tu contraseña temporal antes de continuar.", 403,
                             codigo="cambiar_password")
            if usuario.rol not in roles:
                return error("No tienes permiso para esta sección.", 403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador


# ---------------------------------------------------------------- alcance

def puede_ver_promotor(usuario: Usuario, id_promotor: int) -> bool:
    """Administrador: todos. Supervisor: solo sus promotores. Promotor: él mismo."""
    if usuario.rol == "Administrador":
        return True
    if usuario.rol == "Promotor":
        return usuario.id_usuario == id_promotor
    p = db.session.get(Usuario, id_promotor)
    return p is not None and p.rol == "Promotor" and p.id_supervisor == usuario.id_usuario


def filtro_promotores(usuario: Usuario):
    """Condición SQLAlchemy con los promotores que el usuario puede consultar."""
    cond = Usuario.rol == "Promotor"
    if usuario.rol == "Supervisor":
        cond = cond & (Usuario.id_supervisor == usuario.id_usuario)
    elif usuario.rol == "Promotor":
        cond = cond & (Usuario.id_usuario == usuario.id_usuario)
    return cond


def ids_promotores_visibles(usuario: Usuario) -> list[int]:
    return list(db.session.execute(db.select(Usuario.id_usuario).where(filtro_promotores(usuario))).scalars())


def usuario_a_dict(usuario: Usuario) -> dict:
    """Datos públicos del usuario. Nunca incluye el hash de contraseña."""
    return {
        "id_usuario": usuario.id_usuario,
        "nombre_completo": usuario.nombre_completo,
        "correo_electronico": usuario.correo_electronico,
        "telefono": usuario.telefono,
        "rol": usuario.rol,
        "estatus": usuario.estatus,
        "numero_empleado": usuario.numero_empleado,
        "tipo_contrato": usuario.tipo_contrato,
        "fecha_alta": usuario.fecha_alta.isoformat() if usuario.fecha_alta else None,
        "id_supervisor": usuario.id_supervisor,
        "nombre_supervisor": usuario.supervisor.nombre_completo if usuario.supervisor else None,
        "debe_cambiar_password": bool(usuario.debe_cambiar_password),
    }


# ----------------------------------------------------------- idempotencia

def idempotente(tipo: str):
    """Acciones del promotor con encabezado X-Id-Cliente (UUID generado en
    el dispositivo). Si el mismo ID vuelve a llegar —un reintento o la
    sincronización del modo sin conexión— se responde lo mismo que la
    primera vez y la acción no se repite."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            id_cliente = (request.headers.get("X-Id-Cliente") or "").strip()
            if not id_cliente:
                return vista(*args, **kwargs)
            if not UUID_RE.match(id_cliente):
                return error("Identificador de evento no válido.", 400)
            usuario = usuario_actual()
            previo = db.session.execute(
                db.select(EventoCliente).where(
                    EventoCliente.id_usuario == usuario.id_usuario,
                    EventoCliente.id_cliente == id_cliente,
                )
            ).scalar_one_or_none()
            if previo is not None:
                cuerpo = json.loads(previo.respuesta)
                cuerpo["repetido"] = True
                return jsonify(cuerpo), previo.codigo_http

            respuesta = vista(*args, **kwargs)
            resp, codigo = (respuesta if isinstance(respuesta, tuple) else (respuesta, 200))
            # Solo se guardan los resultados definitivos (éxito o regla de
            # negocio). Los 5xx y 401 se pueden reintentar.
            if codigo < 500 and codigo != 401:
                try:
                    db.session.add(EventoCliente(
                        id_usuario=usuario.id_usuario, id_cliente=id_cliente, tipo=tipo,
                        fecha_hora_captura=None, fecha_hora_recepcion=ahora(),
                        codigo_http=codigo, respuesta=json.dumps(resp.get_json()),
                    ))
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
            return resp, codigo

        return envoltura

    return decorador
