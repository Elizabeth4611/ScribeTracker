"""Datos de la pantalla inicial de cada rol.

Cada ruta acepta únicamente su propio rol; el servidor rechaza con 403
cualquier otro, aunque alguien escriba la URL a mano en el navegador.
"""
from flask import Blueprint, jsonify
from sqlalchemy import func

from app.auth import roles_required, usuario_a_dict, usuario_actual
from app.extensions import db
from app.models import Usuario
from app.models.usuario import ESTATUS, ROLES

bp = Blueprint("inicio", __name__, url_prefix="/api/inicio")


@bp.get("/promotor")
@roles_required("Promotor")
def inicio_promotor():
    usuario = usuario_actual()
    supervisor = (
        db.session.get(Usuario, usuario.id_supervisor)
        if usuario.id_supervisor is not None
        else None
    )
    return jsonify(
        usuario=usuario_a_dict(usuario),
        supervisor=(
            {
                "nombre_completo": supervisor.nombre_completo,
                "correo_electronico": supervisor.correo_electronico,
            }
            if supervisor is not None
            else None
        ),
    )


@bp.get("/supervisor")
@roles_required("Supervisor")
def inicio_supervisor():
    usuario = usuario_actual()
    promotores = db.session.execute(
        db.select(Usuario)
        .where(
            Usuario.id_supervisor == usuario.id_usuario,
            Usuario.rol == "Promotor",
        )
        .order_by(Usuario.nombre_completo)
    ).scalars()
    return jsonify(
        usuario=usuario_a_dict(usuario),
        promotores=[
            {
                "id_usuario": p.id_usuario,
                "nombre_completo": p.nombre_completo,
                "correo_electronico": p.correo_electronico,
                "estatus": p.estatus,
            }
            for p in promotores
        ],
    )


@bp.get("/administrador")
@roles_required("Administrador")
def inicio_administrador():
    usuario = usuario_actual()
    filas = db.session.execute(
        db.select(Usuario.rol, Usuario.estatus, func.count()).group_by(
            Usuario.rol, Usuario.estatus
        )
    ).all()

    resumen = {rol: {estatus: 0 for estatus in ESTATUS} for rol in ROLES}
    for rol, estatus, total in filas:
        if rol in resumen and estatus in resumen[rol]:
            resumen[rol][estatus] = total

    return jsonify(
        usuario=usuario_a_dict(usuario),
        resumen_usuarios=resumen,
        total_usuarios=sum(total for _, _, total in filas),
    )
