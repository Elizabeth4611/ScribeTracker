import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


def _database_url() -> URL:
    # Autenticación de Windows (sin usuario ni contraseña en el código).
    # TrustServerCertificate: el Driver 18 cifra por defecto y un SQL Server
    # local usa un certificado propio; solo es aceptable en desarrollo.
    return URL.create(
        "mssql+pyodbc",
        host=os.getenv("DB_SERVER"),
        database=os.getenv("DB_NAME"),
        query={
            "driver": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
            "trusted_connection": "yes",
            "TrustServerCertificate": "yes",
        },
    )


def _env_bool(nombre: str, por_defecto: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave para firmar la cookie de sesión. Se lee de .env y nunca se
    # escribe en el código; create_app() se niega a arrancar sin ella.
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Cookie de sesión: inaccesible desde JavaScript y no enviada en
    # peticiones POST de otros sitios. Sin PERMANENT_SESSION_LIFETIME:
    # la sesión dura hasta cerrar sesión o cerrar el navegador.
    SESSION_COOKIE_NAME = "scribetracker_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # En desarrollo local se usa http; en producción con HTTPS poner
    # SESSION_COOKIE_SECURE=true en .env.
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)

    # Hash de contraseñas (Werkzeug). Las pruebas usan un método más rápido.
    PASSWORD_HASH_METHOD = "scrypt"

    # Evidencias fotográficas: se guardan fuera del código, en
    # backend/instance/evidencias (carpeta ignorada por Git).
    EVIDENCIAS_DIR = os.getenv("EVIDENCIAS_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "instance", "evidencias"
    )
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB por petición
    EVIDENCIA_MAX_BYTES = 5 * 1024 * 1024

    # Correo para enviar credenciales (opcional). Sin MAIL_SERVER, el alta
    # de usuarios muestra la contraseña temporal una sola vez al
    # administrador.
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT", "587")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM")
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
