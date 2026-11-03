"""Gestión de usuarios (RF-03 a RF-07 del apartado 3.6 del ERS)."""
import re
import secrets
import string

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.auth import error, filtro_promotores, roles_required, usuario_a_dict, usuario_actual
from app.extensions import db
from app.models import Asignacion, Ruta, Usuario, Visita
from app.models.usuario import ROLES
from app.servicios.correo import enviar_credenciales
from app.servicios.tiempo import ahora, hoy

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")

CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TELEFONO_RE = re.compile(r"^\+?[0-9 ]{10,15}$")
NUM_EMPLEADO_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")
TIPOS_CONTRATO = ("Planta", "Temporada")


def _password_temporal() -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        p = "".join(secrets.choice(alfabeto) for _ in range(12))
        if any(c.isdigit() for c in p) and any(c.isalpha() for c in p):
            return p


def _validar(datos: dict, existente: Usuario | None = None):
    """Valida y normaliza. Devuelve (campos, errores)."""
    errores = {}
    c = {}
    c["nombre_completo"] = " ".join(str(datos.get("nombre_completo") or "").split())
    c["correo_electronico"] = str(datos.get("correo_electronico") or "").strip().lower()
    c["telefono"] = " ".join(str(datos.get("telefono") or "").split())
    c["numero_empleado"] = str(datos.get("numero_empleado") or "").strip().upper()
    c["rol"] = str(datos.get("rol") or "").strip()
    c["tipo_contrato"] = str(datos.get("tipo_contrato") or "").strip() or None
    sup = datos.get("id_supervisor")
    c["id_supervisor"] = int(sup) if str(sup or "").strip().isdigit() else None

    if not c["nombre_completo"]:
        errores["nombre_completo"] = "El nombre completo es obligatorio."
    elif len(c["nombre_completo"]) > 100:
        errores["nombre_completo"] = "Máximo 100 caracteres."
    if not CORREO_RE.match(c["correo_electronico"]) or len(c["correo_electronico"]) > 100:
        errores["correo_electronico"] = "Escribe un correo electrónico válido."
    # ERS RF-03: teléfono obligatorio (el diccionario lo permitía nulo; la
    # columna sigue admitiendo NULL para no alterar registros anteriores).
    if not TELEFONO_RE.match(c["telefono"]):
        errores["telefono"] = "El teléfono es obligatorio (10 a 15 dígitos)."
    # ERS RF-03: número de empleado obligatorio y único.
    if not NUM_EMPLEADO_RE.match(c["numero_empleado"]):
        errores["numero_empleado"] = "El número de empleado es obligatorio (letras, números o guiones)."
    if c["rol"] not in ROLES:
        errores["rol"] = "Selecciona un rol válido."
    if c["tipo_contrato"] and c["tipo_contrato"] not in TIPOS_CONTRATO:
        errores["tipo_contrato"] = "Tipo de contrato no válido."

    if c["rol"] == "Promotor":
        sup_u = db.session.get(Usuario, c["id_supervisor"]) if c["id_supervisor"] else None
        if sup_u is None or sup_u.rol != "Supervisor" or not sup_u.esta_activo:
            errores["id_supervisor"] = "Asigna un supervisor activo al promotor."
    else:
        c["id_supervisor"] = None

    yo = existente.id_usuario if existente else -1
    if "correo_electronico" not in errores:
        dup = db.session.execute(db.select(Usuario.id_usuario).where(
            Usuario.correo_electronico == c["correo_electronico"], Usuario.id_usuario != yo)).first()
        if dup:
            errores["correo_electronico"] = "Ya existe un usuario con ese correo."
    if "numero_empleado" not in errores:
        dup = db.session.execute(db.select(Usuario.id_usuario).where(
            Usuario.numero_empleado == c["numero_empleado"], Usuario.id_usuario != yo)).first()
        if dup:
            errores["numero_empleado"] = "Ya existe un usuario con ese número de empleado."
    return c, errores


def _liberar_promotor(promotor: Usuario, motivo: str) -> int:
    """RF-06: al dar de baja a un promotor se liberan sus tiendas. Se cancelan
    las asignaciones futuras y las de hoy que aún no tienen visita; las
    pasadas se conservan como historial. Sus rutas pasan a Inactiva."""
    con_visita = db.select(Visita.id_asignacion)
    asignaciones = db.session.execute(db.select(Asignacion).where(
        Asignacion.id_promotor == promotor.id_usuario,
        Asignacion.estado == "Activa",
        Asignacion.fecha >= hoy(),
        Asignacion.id_asignacion.not_in(con_visita),
    )).scalars().all()
    for a in asignaciones:
        a.estado = "Cancelada"
        a.fecha_cancelacion = ahora()
        a.motivo_cancelacion = motivo
    for r in db.session.execute(db.select(Ruta).where(
            Ruta.id_promotor == promotor.id_usuario, Ruta.estado == "Activa")).scalars():
        r.estado = "Inactiva"
    return len(asignaciones)


@bp.get("")
@roles_required("Administrador", "Supervisor")
def listar():
    yo = usuario_actual()
    q = (request.args.get("q") or "").strip()
    rol = request.args.get("rol") or ""
    estatus = request.args.get("estatus") or ""
    pagina = max(int(request.args.get("pagina", 1) or 1), 1)
    por_pagina = min(max(int(request.args.get("por_pagina", 10) or 10), 1), 100)

    consulta = db.select(Usuario)
    if yo.rol == "Supervisor":
        consulta = consulta.where(filtro_promotores(yo))
    if q:
        patron = f"%{q}%"
        consulta = consulta.where(or_(
            Usuario.nombre_completo.ilike(patron),
            Usuario.numero_empleado.ilike(patron),
            Usuario.correo_electronico.ilike(patron),
        ))
    if rol in ROLES:
        consulta = consulta.where(Usuario.rol == rol)
    if estatus in ("Activo", "Inactivo"):
        consulta = consulta.where(Usuario.estatus == estatus)

    total = db.session.execute(db.select(func.count()).select_from(consulta.subquery())).scalar_one()
    filas = db.session.execute(
        consulta.order_by(Usuario.nombre_completo).offset((pagina - 1) * por_pagina).limit(por_pagina)
    ).scalars().all()
    return jsonify(usuarios=[usuario_a_dict(u) for u in filas], total=total,
                   pagina=pagina, por_pagina=por_pagina)


@bp.get("/supervisores")
@roles_required("Administrador")
def supervisores():
    filas = db.session.execute(db.select(Usuario).where(
        Usuario.rol == "Supervisor", Usuario.estatus == "Activo").order_by(Usuario.nombre_completo)).scalars()
    return jsonify(supervisores=[{"id_usuario": u.id_usuario, "nombre_completo": u.nombre_completo} for u in filas])


@bp.get("/<int:id_usuario>")
@roles_required("Administrador", "Supervisor")
def detalle(id_usuario):
    yo = usuario_actual()
    u = db.session.get(Usuario, id_usuario)
    if u is None or (yo.rol == "Supervisor" and not (u.rol == "Promotor" and u.id_supervisor == yo.id_usuario)):
        return error("Usuario no encontrado.", 404)
    return jsonify(usuario=usuario_a_dict(u))


@bp.post("")
@roles_required("Administrador")
def crear():
    if not request.is_json:
        return error("La petición debe enviarse como JSON.", 415)
    campos, errores = _validar(request.get_json(silent=True) or {})
    if errores:
        return error("Revisa los campos marcados.", 400, campos=errores)

    temporal = _password_temporal()
    u = Usuario(**campos, estatus="Activo", fecha_alta=ahora(), debe_cambiar_password=True)
    u.set_password(temporal)
    db.session.add(u)
    db.session.commit()  # 1) el alta queda confirmada antes de intentar el correo

    envio = enviar_credenciales(u.correo_electronico, u.nombre_completo, temporal)  # 2) envío aparte
    acceso = {"envio_correo": envio}
    if envio != "enviado":
        acceso["password_temporal"] = temporal
        acceso["aviso"] = ("No se envió el correo. Entrega esta contraseña temporal al usuario; "
                           "se muestra una sola vez y deberá cambiarla al entrar.")
    return jsonify(mensaje="Usuario registrado correctamente.", usuario=usuario_a_dict(u), acceso=acceso), 201


@bp.put("/<int:id_usuario>")
@roles_required("Administrador")
def editar(id_usuario):
    if not request.is_json:
        return error("La petición debe enviarse como JSON.", 415)
    yo = usuario_actual()
    u = db.session.get(Usuario, id_usuario)
    if u is None:
        return error("Usuario no encontrado.", 404)
    campos, errores = _validar(request.get_json(silent=True) or {}, existente=u)
    if errores:
        return error("Revisa los campos marcados.", 400, campos=errores)

    aviso = None
    if campos["rol"] != u.rol:
        if u.id_usuario == yo.id_usuario:
            return error("No puedes cambiar tu propio rol.", 409)
        if u.rol == "Supervisor":
            a_cargo = db.session.execute(db.select(func.count()).where(
                Usuario.id_supervisor == u.id_usuario, Usuario.estatus == "Activo")).scalar_one()
            if a_cargo:
                return error(f"Este supervisor tiene {a_cargo} promotor(es) activos. Reasígnalos antes de cambiar su rol.", 409)
        if u.rol == "Promotor":
            n = _liberar_promotor(u, "Cambio de rol")
            aviso = f"Se liberaron {n} asignación(es) futura(s) del promotor."
    for k, v in campos.items():
        setattr(u, k, v)
    db.session.commit()
    return jsonify(mensaje="Datos actualizados correctamente.", usuario=usuario_a_dict(u), aviso=aviso)


@bp.post("/<int:id_usuario>/desactivar")
@roles_required("Administrador")
def desactivar(id_usuario):
    yo = usuario_actual()
    u = db.session.get(Usuario, id_usuario)
    if u is None:
        return error("Usuario no encontrado.", 404)
    if u.id_usuario == yo.id_usuario:
        return error("No puedes desactivar tu propia cuenta.", 409)
    if not u.esta_activo:
        return error("El usuario ya está inactivo.", 409)
    if u.rol == "Supervisor":
        a_cargo = db.session.execute(db.select(func.count()).where(
            Usuario.id_supervisor == u.id_usuario, Usuario.estatus == "Activo")).scalar_one()
        if a_cargo:
            return error(f"Este supervisor tiene {a_cargo} promotor(es) activos. Reasígnalos a otro supervisor primero.", 409)
    liberadas = _liberar_promotor(u, "Baja del promotor") if u.rol == "Promotor" else 0
    u.estatus = "Inactivo"  # baja lógica: el registro y su historial se conservan
    u.fecha_baja = ahora()
    db.session.commit()
    return jsonify(mensaje="Usuario desactivado. Ya no puede iniciar sesión.",
                   usuario=usuario_a_dict(u), asignaciones_liberadas=liberadas)


@bp.post("/<int:id_usuario>/reactivar")
@roles_required("Administrador")
def reactivar(id_usuario):
    u = db.session.get(Usuario, id_usuario)
    if u is None:
        return error("Usuario no encontrado.", 404)
    if u.esta_activo:
        return error("El usuario ya está activo.", 409)
    if u.rol == "Promotor":
        sup = db.session.get(Usuario, u.id_supervisor) if u.id_supervisor else None
        if sup is None or not sup.esta_activo:
            return error("Asigna primero un supervisor activo a este promotor (edítalo).", 409)
    u.estatus = "Activo"
    u.fecha_baja = None
    db.session.commit()
    return jsonify(mensaje="Usuario reactivado.", usuario=usuario_a_dict(u))


@bp.post("/<int:id_usuario>/restablecer-password")
@roles_required("Administrador")
def restablecer_password(id_usuario):
    u = db.session.get(Usuario, id_usuario)
    if u is None:
        return error("Usuario no encontrado.", 404)
    temporal = _password_temporal()
    u.set_password(temporal)
    u.debe_cambiar_password = True
    u.intentos_fallidos = 0
    db.session.commit()
    envio = enviar_credenciales(u.correo_electronico, u.nombre_completo, temporal)
    acceso = {"envio_correo": envio}
    if envio != "enviado":
        acceso["password_temporal"] = temporal
        acceso["aviso"] = "Entrega esta contraseña temporal al usuario; se muestra una sola vez."
    return jsonify(mensaje="Contraseña temporal generada.", acceso=acceso)
