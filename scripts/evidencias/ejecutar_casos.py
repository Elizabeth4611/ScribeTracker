"""Ejecuta cada caso del reporte contra SQL Server (base SEPARADA
ScribeTracker_Pruebas) y guarda la salida real de pytest en
docs/evidencias/salidas/CP-xx_sqlserver.txt. No modifica el código."""
import os
import platform
import subprocess
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
BACKEND = os.path.join(RAIZ, "backend")
SALIDAS = os.path.join(RAIZ, "docs", "evidencias", "salidas")
sys.path.insert(0, AQUI)
from casos import CASOS  # noqa: E402

os.makedirs(SALIDAS, exist_ok=True)
entorno = dict(os.environ, ST_BD_PRUEBAS="ScribeTracker_Pruebas", PYTHONIOENCODING="utf-8")
for cid, fallo, nombre, prueba in CASOS:
    if not prueba:
        continue
    cmd = [sys.executable, "-m", "pytest", prueba, "-v", "-p", "no:cacheprovider", "--no-header", "-rA", "--color=no"]
    inicio = datetime.now()
    r = subprocess.run(cmd, cwd=BACKEND, env=entorno, capture_output=True, text=True, encoding="utf-8")
    cab = (f"{cid} · {nombre}\n"
           f"Fecha y hora: {inicio:%d/%m/%Y %H:%M:%S}  ·  Equipo: {platform.node()}  ·  Windows {platform.release()}  ·  Python {platform.python_version()}\n"
           f"Base de datos: SQL Server, base de pruebas ScribeTracker_Pruebas (ST_BD_PRUEBAS)\n"
           f"Carpeta: C:\\ScribeTracker\\backend\n"
           f"> set ST_BD_PRUEBAS=ScribeTracker_Pruebas\n"
           f"> python -m pytest {prueba} -v\n\n")
    with open(os.path.join(SALIDAS, f"{cid}_sqlserver.txt"), "w", encoding="utf-8") as fh:
        fh.write(cab + r.stdout + (r.stderr or ""))
    print(cid, "código de salida", r.returncode)
