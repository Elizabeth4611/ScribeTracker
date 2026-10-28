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