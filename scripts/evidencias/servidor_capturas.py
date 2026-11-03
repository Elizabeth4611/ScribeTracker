"""Servidor para las capturas de interfaz.

Sirve la API de Flask y el build de producción de Angular en el mismo
puerto, con una base NUEVA poblada con datos de demostración (borra y crea
las tablas). Uso:
    python servidor_capturas.py <dist> <bd.sqlite> <puerto>              SQLite
    python servidor_capturas.py <dist> mssql:ScribeTracker_Pruebas <puerto>   SQL Server
En modo SQL Server solo acepta una base cuyo nombre termine en "_Pruebas" y
que no sea la base real de backend/.env (DB_NAME).
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))
from flask import send_from_directory  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Asignacion, Tienda, Usuario  # noqa: E402
from app.servicios import parametros  # noqa: E402
from config import Config  # noqa: E402

DIST, BD, PUERTO = sys.argv[1], sys.argv[2], int(sys.argv[3])
# Contraseña de los usuarios de demostración: no se escribe en el código; la da
# el orquestador (aleatoria en cada ejecución) en la variable ST_DEMO_PASSWORD.
CLAVE_DEMO = os.environ.get("ST_DEMO_PASSWORD") or sys.exit("Falta la variable ST_DEMO_PASSWORD")


def _uri():
    if not BD.startswith("mssql:"):
        return f"sqlite:///{BD}", os.path.join(os.path.dirname(os.path.abspath(BD)), "evidencias")
    nombre = BD.split(":", 1)[1]
    # Protección: sembrar() hace drop_all(); nunca debe tocar la base real.
    if not nombre.endswith("_Pruebas") or nombre == os.getenv("DB_NAME"):
        raise SystemExit(f"Base no permitida para capturas: {nombre}. Usa una base *_Pruebas distinta de DB_NAME.")
    from sqlalchemy.engine import URL
    uri = URL.create("mssql+pyodbc", host=os.getenv("DB_SERVER"), database=nombre, query={
        "driver": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "trusted_connection": "yes", "TrustServerCertificate": "yes"})
    return uri, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "evidencias_capturas")


URI, CARPETA_FOTOS = _uri()


class ConfigCapturas(Config):
    SQLALCHEMY_DATABASE_URI = URI
    SECRET_KEY = "solo-capturas"
    EVIDENCIAS_DIR = CARPETA_FOTOS


app = create_app(ConfigCapturas)


@app.get("/", defaults={"ruta": ""})
@app.get("/<path:ruta>")
def spa(ruta):
    if ruta.startswith("api/"):
        return {"error": "No encontrado"}, 404
    destino = os.path.join(DIST, ruta)
    if ruta and os.path.isfile(destino):
        return send_from_directory(DIST, ruta)
    return send_from_directory(DIST, "index.html")


TIENDAS = [
    ("Walmart", "Walmart", "Torres Landa", "Blvd. Juan Alonso de Torres 2002, León", "Norte", 21.1458, -101.6893, 90, 150),
    ("Soriana", "Soriana", "San Juan Bosco", "Blvd. San Juan Bosco 3802, León", "Poniente", 21.1395, -101.7104, 80, 90),
    ("Office Depot", "Office Depot", "Altacia", "Blvd. Aeropuerto 104, Plaza Altacia, León", "Oriente", 21.1028, -101.6280, 60, 60),
    ("Bodega Aurrera", "Walmart", "López Mateos", "Blvd. Adolfo López Mateos 1501, León", "Centro", 21.1213, -101.6740, 70, 120),
]


def sembrar():
    db.drop_all()
    db.create_all()
    parametros.sembrar()

    def u(nombre, correo, rol, num, sup=None, estatus="Activo", tipo=None):
        x = Usuario(nombre_completo=nombre, correo_electronico=correo, rol=rol, estatus=estatus, numero_empleado=num,
                    telefono="4771234567", id_supervisor=sup.id_usuario if sup else None, tipo_contrato=tipo,
                    fecha_alta=datetime(2026, 9, 1))
        x.set_password(CLAVE_DEMO)
        db.session.add(x)
        db.session.commit()
        return x

    u("Pablo Galván Romero", "admin@demo.mx", "Administrador", "ADM-01")
    s = u("Juan Antonio Martínez", "supervisor@demo.mx", "Supervisor", "SUP-01")
    p = u("Marco Antonio Solís", "promotor@demo.mx", "Promotor", "SR-092", sup=s, tipo="Temporada")
    u("Julieta Vengas", "julieta@demo.mx", "Promotor", "SR-093", sup=s, tipo="Planta")
    u("Jorge Castillo", "inactivo@demo.mx", "Promotor", "SR-094", sup=s, estatus="Inactivo")
    ts = []
    for nom, cad, suc, dirc, zona, lat, lon, radio, mins in TIENDAS:
        t = Tienda(nombre_comercial=nom, cadena=cad, sucursal=suc, direccion_completa=dirc, zona=zona, latitud=lat,
                   longitud=lon, radio_geocerca_m=radio, tiempo_estimado_min=mins, estatus="Activa", fecha_alta=datetime(2026, 9, 1))
        db.session.add(t)
        ts.append(t)
    db.session.commit()
    hoy = datetime.now().date()
    for i, t in enumerate(ts, 1):
        db.session.add(Asignacion(id_promotor=p.id_usuario, id_tienda=t.id_tienda, fecha=hoy, orden_visita=i,
                                  estado="Activa", id_asignado_por=s.id_usuario, fecha_asignacion=datetime.now()))
    db.session.commit()


with app.app_context():
    sembrar()
    print("Base de capturas:", db.engine.url.render_as_string(hide_password=True), flush=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
