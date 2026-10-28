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


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False