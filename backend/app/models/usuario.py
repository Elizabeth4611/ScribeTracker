from flask import current_app, has_app_context
from sqlalchemy import CheckConstraint, Index, text
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

ROLES = ("Promotor", "Supervisor", "Administrador")
ESTATUS = ("Activo", "Inactivo")


class Usuario(db.Model):
    __tablename__ = "Usuario"
    __table_args__ = (
        CheckConstraint(
            "Rol IN ('Promotor', 'Supervisor', 'Administrador')",
            name="CK_Usuario_Rol",
        ),
        CheckConstraint(
            "Estatus IN ('Activo', 'Inactivo')",
            name="CK_Usuario_Estatus",
        ),
        # Único solo cuando tiene valor: los usuarios creados antes de
        # agregar la columna pueden quedar sin número hasta editarlos.
        Index(
            "UX_Usuario_Numero_Empleado",
            "Numero_Empleado",
            unique=True,
            mssql_where=text("Numero_Empleado IS NOT NULL"),
            sqlite_where=text("Numero_Empleado IS NOT NULL"),
        ),
    )

    id_usuario = db.Column("ID_Usuario", db.Integer, primary_key=True)
    nombre_completo = db.Column("Nombre_Completo", db.String(100), nullable=False)
    correo_electronico = db.Column(
        "Correo_Electronico", db.String(100), unique=True, nullable=False
    )
    telefono = db.Column("Telefono", db.String(15), nullable=True)
    rol = db.Column("Rol", db.String(20), nullable=False)
    password_hash = db.Column("Password_Hash", db.String(255), nullable=False)
    estatus = db.Column(
        "Estatus",
        db.String(20),
        nullable=False,
        default="Activo",
        server_default="Activo",
    )
    id_supervisor = db.Column(
        "ID_Supervisor",
        db.Integer,
        db.ForeignKey("Usuario.ID_Usuario"),
        nullable=True,
    )

    # --- Columnas agregadas en la etapa 2 (migración 2b7c...) ---
    numero_empleado = db.Column("Numero_Empleado", db.String(20), nullable=True)
    tipo_contrato = db.Column("Tipo_Contrato", db.String(20), nullable=True)  # Planta / Temporada
    fecha_alta = db.Column("Fecha_Alta", db.DateTime, nullable=True)
    debe_cambiar_password = db.Column(
        "Debe_Cambiar_Password", db.Boolean, nullable=False,
        default=False, server_default=text("0"),
    )
    # Registro de intentos fallidos. La política de bloqueo (cuántos
    # intentos y por cuánto tiempo) sigue PENDIENTE de definir: se cuentan
    # pero no se bloquea la cuenta.
    intentos_fallidos = db.Column(
        "Intentos_Fallidos", db.Integer, nullable=False,
        default=0, server_default=text("0"),
    )
    ultimo_intento_fallido = db.Column("Ultimo_Intento_Fallido", db.DateTime, nullable=True)
    fecha_baja = db.Column("Fecha_Baja", db.DateTime, nullable=True)

    supervisor = db.relationship("Usuario", remote_side=[id_usuario], uselist=False)

    def set_password(self, password: str) -> None:
        metodo = "scrypt"
        if has_app_context():
            metodo = current_app.config.get("PASSWORD_HASH_METHOD", "scrypt")
        self.password_hash = generate_password_hash(password, method=metodo)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def esta_activo(self) -> bool:
        return self.estatus == "Activo"
