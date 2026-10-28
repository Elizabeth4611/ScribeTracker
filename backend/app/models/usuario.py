from sqlalchemy import CheckConstraint
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

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def esta_activo(self) -> bool:
        return self.estatus == "Activo"