import click

from app.extensions import db
from app.models import Usuario


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--nombre", prompt="Nombre completo")
    @click.option("--correo", prompt="Correo electrónico")
    @click.password_option("--password", prompt="Contraseña")
    def create_admin(nombre, correo, password):
        """Crea el primer usuario con rol Administrador."""
        correo = correo.strip().lower()

        if len(password) < 8:
            raise click.ClickException(
                "La contraseña debe tener al menos 8 caracteres."
            )

        existente = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == correo)
        ).scalar_one_or_none()
        if existente is not None:
            raise click.ClickException("Ya existe un usuario con ese correo.")

        admin = Usuario(
            nombre_completo=nombre.strip(),
            correo_electronico=correo,
            rol="Administrador",
            estatus="Activo",
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrador creado con ID {admin.id_usuario}.")

    @app.cli.command("create-usuario")
    @click.option("--nombre", prompt="Nombre completo")
    @click.option("--correo", prompt="Correo electrónico")
    @click.option(
        "--rol",
        prompt="Rol",
        type=click.Choice(["Promotor", "Supervisor", "Administrador"]),
    )
    @click.option(
        "--estatus",
        default="Activo",
        show_default=True,
        type=click.Choice(["Activo", "Inactivo"]),
    )
    @click.option(
        "--supervisor",
        "correo_supervisor",
        default="",
        help="Correo del supervisor (solo para promotores).",
    )
    @click.password_option("--password", prompt="Contraseña")
    def create_usuario(nombre, correo, rol, estatus, correo_supervisor, password):
        """Crea un usuario con el rol indicado (útil para pruebas)."""
        correo = correo.strip().lower()

        if len(password) < 8:
            raise click.ClickException(
                "La contraseña debe tener al menos 8 caracteres."
            )

        existente = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == correo)
        ).scalar_one_or_none()
        if existente is not None:
            raise click.ClickException("Ya existe un usuario con ese correo.")

        id_supervisor = None
        correo_supervisor = correo_supervisor.strip().lower()
        if correo_supervisor:
            if rol != "Promotor":
                raise click.ClickException(
                    "Solo los promotores tienen supervisor."
                )
            supervisor = db.session.execute(
                db.select(Usuario).where(
                    Usuario.correo_electronico == correo_supervisor
                )
            ).scalar_one_or_none()
            if supervisor is None or supervisor.rol != "Supervisor":
                raise click.ClickException(
                    "No existe un supervisor con ese correo."
                )
            id_supervisor = supervisor.id_usuario

        usuario = Usuario(
            nombre_completo=nombre.strip(),
            correo_electronico=correo,
            rol=rol,
            estatus=estatus,
            id_supervisor=id_supervisor,
        )
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()
        click.echo(f"{rol} creado con ID {usuario.id_usuario}.")