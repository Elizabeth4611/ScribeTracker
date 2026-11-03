"""Revisión de secretos antes de subir a GitHub. Nunca imprime los valores.

Uso: python scripts\revisar_antes_de_subir.py <carpeta_a_revisar>
Falla (código 1) si en la carpeta (sin contar .git) hay:
- archivos .env (salvo .env.example), *.env o carpetas *_respaldo;
- la carpeta scripts/logs (contiene las contraseñas de los usuarios de prueba);
- el valor de SECRET_KEY o MAIL_PASSWORD de backend/.env, o alguna contraseña de
  scripts/logs/usuarios_prueba.txt, escrito dentro de cualquier archivo.
"""
import os
import re
import sys

ORIGEN = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
destino = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ORIGEN)

secretos = []
env = os.path.join(ORIGEN, "backend", ".env")
if os.path.isfile(env):
    for linea in open(env, encoding="utf-8", errors="ignore"):
        m = re.match(r"\s*(SECRET_KEY|MAIL_PASSWORD)\s*=\s*(.+?)\s*$", linea)
        if m and len(m.group(2).strip("\"'")) >= 6:
            secretos.append((m.group(1), m.group(2).strip("\"'")))
usuarios = os.path.join(ORIGEN, "scripts", "logs", "usuarios_prueba.txt")
if os.path.isfile(usuarios):
    for i, linea in enumerate(open(usuarios, encoding="utf-8", errors="ignore"), 1):
        m = re.search(r"ña:\s*(\S+)", linea)
        if m:
            secretos.append((f"contraseña de prueba {i}", m.group(1)))

problemas = []
revisados = 0
for raiz, dirs, archivos in os.walk(destino):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv")]
    rel = os.path.relpath(raiz, destino).replace(os.sep, "/")
    for d in dirs:
        if d.endswith("_respaldo"):
            problemas.append(f"carpeta de respaldo: {rel}/{d}")
        if rel == "scripts" and d == "logs":
            problemas.append("carpeta scripts/logs (contraseñas de prueba)")
    for f in archivos:
        ruta = os.path.join(raiz, f)
        nombre = os.path.relpath(ruta, destino).replace(os.sep, "/")
        if (f == ".env" or f.endswith(".env") or (f.startswith(".env.") and f != ".env.example")):
            problemas.append(f"archivo de entorno: {nombre}")
        if os.path.getsize(ruta) > 5_000_000 or f.lower().endswith((".png", ".jpg", ".pdf", ".zip", ".tgz")):
            continue
        try:
            texto = open(ruta, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        revisados += 1
        for etiqueta, valor in secretos:
            if valor in texto:
                problemas.append(f"{nombre} contiene {etiqueta}")

print(f"Carpeta revisada: {destino}")
print(f"Archivos de texto revisados: {revisados} · valores secretos buscados: {len(secretos)}")
if problemas:
    print("NO SUBIR. Problemas encontrados:")
    for p in problemas:
        print("  -", p)
    sys.exit(1)
print("OK: no se encontraron archivos .env, respaldos, logs ni valores secretos.")
