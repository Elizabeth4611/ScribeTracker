"""Prepara la base de datos de Azure SQL para ScribeTracker.

1. Se conecta a Azure con el usuario de SQL (la contraseña se teclea aquí y no se guarda).
2. Crea las tablas con las mismas migraciones de Alembic que la base local.
3. (Opcional) Copia los datos de la base LOCAL (la de backend/.env) a Azure, tabla por
   tabla, conservando los Id. Solo copia a tablas que estén vacías en Azure, así que se
   puede ejecutar dos veces sin duplicar nada.

Las fotos (backend/instance/evidencias) no se copian: los registros quedan, pero las fotos
anteriores no se verán en la nube.
"""
import getpass
import os
import sys
import time

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BACKEND, ".env"))   # la ruta explícita: load_dotenv() buscaría desde scripts/
LOCAL_SERVER, LOCAL_BD = os.getenv("DB_SERVER"), os.getenv("DB_NAME")
DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

from sqlalchemy import MetaData, create_engine, func, select, text  # noqa: E402
from sqlalchemy.engine import URL  # noqa: E402


def preguntar(texto, defecto):
    r = input(f"{texto} [{defecto}]: ").strip()
    return r or defecto


print("=== Base de datos de ScribeTracker en Azure ===\n")
servidor = preguntar("Servidor de Azure", os.getenv("AZURE_SQL_SERVER", ""))
if "." not in servidor:
    servidor += ".database.windows.net"
bd = preguntar("Base de datos", "ScribeTracker")
usuario = preguntar("Usuario administrador de SQL", os.getenv("AZURE_SQL_USER", ""))
clave = getpass.getpass("Contraseña de SQL (no se ve al escribir): ")

url_azure = URL.create("mssql+pyodbc", username=usuario, password=clave, host=servidor, port=1433, database=bd,
                       query={"driver": DRIVER, "Encrypt": "yes", "TrustServerCertificate": "no", "Connection Timeout": "60"})
azure = create_engine(url_azure, fast_executemany=True)

print("\n1/3 Conectando a Azure (si la base estaba en pausa tarda hasta 1 minuto)...")
for intento in range(1, 6):
    try:
        with azure.connect() as c:
            print("    Conectado:", c.execute(text("SELECT @@VERSION")).scalar().splitlines()[0])
        break
    except Exception as e:
        msg = str(e)
        if "40615" in msg or "Client with IP address" in msg:
            print("\nERROR: el firewall de Azure no deja entrar a esta laptop.")
            print("En el portal: servidor SQL → Redes → 'Agregar la dirección IPv4 del cliente' → Guardar. Luego repite.")
            sys.exit(1)
        if "18456" in msg or "Login failed" in msg:
            print("\nERROR: usuario o contraseña de SQL incorrectos.")
            sys.exit(1)
        print(f"    intento {intento}: todavía no responde ({msg.splitlines()[0][:120]})")
        time.sleep(15)
else:
    print("\nERROR: no se pudo conectar a Azure.")
    sys.exit(1)

print("\n2/3 Creando las tablas (migraciones de Alembic)...")
os.environ.update({"DB_SERVER": servidor, "DB_NAME": bd, "DB_USER": usuario, "DB_PASSWORD": clave})
from app import create_app  # noqa: E402
from flask_migrate import upgrade  # noqa: E402

app = create_app()
with app.app_context():
    upgrade(directory=os.path.join(BACKEND, "migrations"))
print("    Tablas listas.")

r = input("\n3/3 ¿Copiar los datos de tu base LOCAL (usuarios, tiendas, rutas, jornadas...) a Azure? (s/n): ")
if r.strip().lower() not in ("s", "si", "sí"):
    print("No se copiaron datos. Listo.")
    sys.exit(0)

local = create_engine(URL.create("mssql+pyodbc", host=LOCAL_SERVER, database=LOCAL_BD,
                                 query={"driver": DRIVER, "trusted_connection": "yes", "TrustServerCertificate": "yes"}))
try:
    with local.connect() as c:
        c.execute(text("SELECT 1"))
except Exception:
    print(f"\nERROR: no se pudo conectar a tu SQL Server LOCAL ({LOCAL_SERVER}, base {LOCAL_BD}).")
    print("Si está apagado: ejecuta scripts\\iniciar_sql.bat (pide permiso de administrador)")
    print("y vuelve a abrir este programa. Las tablas de Azure ya quedaron creadas; no se duplica nada.")
    sys.exit(1)
meta_az, meta_lo = MetaData(), MetaData()
meta_az.reflect(azure)
meta_lo.reflect(local)
total = 0
with azure.begin() as dest, local.connect() as orig:
    for t in meta_az.sorted_tables:
        if t.name == "alembic_version" or t.name not in meta_lo.tables:
            continue
        if dest.execute(select(func.count()).select_from(t)).scalar():
            print(f"    {t.name}: ya tiene datos en Azure, se deja como está")
            continue
        origen = meta_lo.tables[t.name]
        columnas = [c.name for c in t.columns if c.name in origen.columns]
        consulta = select(*[origen.c[c] for c in columnas]).order_by(*origen.primary_key.columns)
        filas = [dict(f._mapping) for f in orig.execute(consulta)]
        if not filas:
            continue
        identidad = dest.execute(text("SELECT COUNT(*) FROM sys.identity_columns WHERE object_id = OBJECT_ID(:t)"),
                                 {"t": t.name}).scalar()
        if identidad:
            dest.execute(text(f"SET IDENTITY_INSERT [{t.name}] ON"))
        for i in range(0, len(filas), 500):
            dest.execute(t.insert(), filas[i:i + 500])
        if identidad:
            dest.execute(text(f"SET IDENTITY_INSERT [{t.name}] OFF"))
        print(f"    {t.name}: {len(filas)} filas")
        total += len(filas)
print(f"\nListo: {total} filas copiadas a Azure.")
