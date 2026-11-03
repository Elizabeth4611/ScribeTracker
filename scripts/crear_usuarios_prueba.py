"""Crea usuarios de prueba (Administrador, Supervisor, Promotor y Promotor Inactivo).

Las contraseñas se generan al azar y se guardan solo en
scripts\\logs\\usuarios_prueba.txt (carpeta ignorada por Git).
No modifica usuarios existentes: si un correo ya existe, lo omite.
"""
import os
import secrets
import sys

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
os.chdir(BACKEND)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Usuario  # noqa: E402

USUARIOS = [
    ("Administrador de Prueba", "admin.prueba@scribetracker.test", "Administrador", "Activo", None),
    ("Supervisor de Prueba", "supervisor.prueba@scribetracker.test", "Supervisor", "Activo", None),
    ("Promotor de Prueba", "promotor.prueba@scribetracker.test", "Promotor", "Activo",
     "supervisor.prueba@scribetracker.test"),
    ("Promotor Inactivo de Prueba", "inactivo.prueba@scribetracker.test", "Promotor", "Inactivo",
     "supervisor.prueba@scribetracker.test"),
]

salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "usuarios_prueba.txt")
os.makedirs(os.path.dirname(salida), exist_ok=True)

app = create_app()
with app.app_context():
    lineas = []
    for nombre, correo, rol, estatus, correo_sup in USUARIOS:
        existe = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == correo)
        ).scalar_one_or_none()
        if existe is not None:
            print(f"Ya existe, se omite: {correo}")
            continue
        id_sup = None
        if correo_sup:
            sup = db.session.execute(
                db.select(Usuario).where(Usuario.correo_electronico == correo_sup)
            ).scalar_one()
            id_sup = sup.id_usuario
        password = secrets.token_urlsafe(12)
        u = Usuario(nombre_completo=nombre, correo_electronico=correo, rol=rol,
                    estatus=estatus, id_supervisor=id_sup)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        lineas.append(f"{rol} ({estatus}): {correo}  contraseña: {password}")
        print(f"Creado: {rol} ({estatus}) {correo}")

    if lineas:
        with open(salida, "a", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")
        print(f"Contraseñas guardadas en {salida}")

    otros = db.session.execute(
        db.select(Usuario.correo_electronico).where(
            Usuario.rol == "Administrador",
            Usuario.correo_electronico.notlike("%@scribetracker.test"),
        )
    ).scalars().all()
    for correo in otros:
        print(f"Administrador existente: {correo}")
