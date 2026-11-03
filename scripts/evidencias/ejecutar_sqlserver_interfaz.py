"""Evidencias con SQL Server (base de pruebas ScribeTracker_Pruebas) en la laptop.

Pasos, en orden, con registro en scripts/logs/sqlserver_interfaz.log:
1. Resultados HTTP obtenidos de los casos CP del reporte (pytest + JUnit)
   -> docs/evidencias/salidas/obtenidos_sqlserver.xml
2. Servidor de capturas (Flask + build de Angular) sobre ScribeTracker_Pruebas
   y recorrido completo de la interfaz -> docs/evidencias/sqlserver/
3. Base sembrada de nuevo y caso CP-28 (F08) -> docs/evidencias/CP-28_sqlserver.png
Nunca usa la base real: servidor_capturas.py rechaza cualquier base que no
termine en _Pruebas o que sea DB_NAME. Uso: python ejecutar_sqlserver_interfaz.py
"""
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
BACKEND = os.path.join(RAIZ, "backend")
DIST = os.path.join(RAIZ, "frontend", "dist", "frontend", "browser")
EVID = os.path.join(RAIZ, "docs", "evidencias")
SAL = os.path.join(EVID, "salidas")
SQLUI = os.path.join(EVID, "sqlserver")
BD = "ScribeTracker_Pruebas"
PUERTO = 8765
URL = f"http://127.0.0.1:{PUERTO}"
ENTORNO = "Angular (build de producción) + Flask · SQL Server, base de pruebas ScribeTracker_Pruebas · laptop"
PY = sys.executable
# Contraseña aleatoria para los usuarios de demostración de esta ejecución (no se guarda ni se imprime).
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", ST_BD_PRUEBAS=BD, ST_DEMO_PASSWORD=secrets.token_urlsafe(12))


def log(msg):
    print(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {msg}", flush=True)


def correr(args, cwd=RAIZ, timeout=900):
    log("> " + " ".join(args))
    r = subprocess.run(args, cwd=cwd, env=ENV, timeout=timeout)
    log(f"código de salida: {r.returncode}")
    return r.returncode


def iniciar_servidor():
    salida = open(os.path.join(RAIZ, "scripts", "logs", "servidor_capturas_sqlserver.log"), "a", encoding="utf-8")
    p = subprocess.Popen([PY, os.path.join(AQUI, "servidor_capturas.py"), DIST, f"mssql:{BD}", str(PUERTO)],
                         cwd=BACKEND, env=ENV, stdout=salida, stderr=subprocess.STDOUT)
    for _ in range(90):
        time.sleep(1)
        if p.poll() is not None:
            raise SystemExit(f"El servidor de capturas terminó con código {p.returncode}; revisa servidor_capturas_sqlserver.log")
        try:
            if urllib.request.urlopen(f"{URL}/login", timeout=3).status == 200:
                log(f"servidor de capturas listo en {URL} (base {BD})")
                return p
        except OSError:
            pass
    p.kill()
    raise SystemExit("El servidor de capturas no respondió en 90 s")


def detener(p):
    p.terminate()
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        p.kill()
    log("servidor de capturas detenido")


def main():
    os.makedirs(SAL, exist_ok=True)
    os.makedirs(SQLUI, exist_ok=True)
    log(f"Equipo: {os.environ.get('COMPUTERNAME', '?')} · Python {sys.version.split()[0]} · base {BD}")
    if not os.path.isfile(os.path.join(DIST, "index.html")):
        raise SystemExit("No existe el build de Angular; ejecuta scripts\\construir_frontend.bat")

    # 1. Resultados HTTP con SQL Server
    sys.path.insert(0, AQUI)
    from casos import CASOS
    ids = [c[3] for c in CASOS if c[3]]
    rc1 = correr([PY, "-m", "pytest", *ids, "-q", "-o", "junit_family=legacy",
                  f"--junitxml={os.path.join(SAL, 'obtenidos_sqlserver.xml')}"], cwd=BACKEND)

    # 2. Recorrido de la interfaz sobre SQL Server
    p = iniciar_servidor()
    try:
        rc2 = correr([PY, os.path.join(AQUI, "capturas_interfaz.py"), URL, SQLUI, ENTORNO])
    finally:
        detener(p)

    # 3. CP-28 (F08) con la base sembrada de nuevo
    p = iniciar_servidor()
    try:
        rc3 = correr([PY, os.path.join(AQUI, "reproducir_sincronizacion.py"), URL, EVID, "sqlserver", ENTORNO])
    finally:
        detener(p)
    origen_json = os.path.join(EVID, "CP-28_sqlserver.json")
    if os.path.isfile(origen_json):
        os.replace(origen_json, os.path.join(SAL, "CP-28_sqlserver.json"))

    log(f"RESUMEN pytest={rc1} interfaz={rc2} cp28={rc3}")
    return 0 if rc1 == rc2 == rc3 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
