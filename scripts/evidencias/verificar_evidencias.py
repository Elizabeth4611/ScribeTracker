"""Comprueba que cada imagen citada en docs/REPORTE_PRUEBAS.md existe y se abre,
y lista las imágenes de docs/evidencias que el reporte no cita."""
import os
import re
import sys

from PIL import Image

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
md = open(os.path.join(RAIZ, "docs", "REPORTE_PRUEBAS.md"), encoding="utf-8").read()
citadas = sorted(set(re.findall(r"!\[[^\]]*\]\((evidencias/[^)]+)\)", md)))
errores = 0
for rel in citadas:
    ruta = os.path.join(RAIZ, "docs", rel)
    try:
        with Image.open(ruta) as im:
            im.load()
            print(f"OK   {rel}  {im.size[0]}x{im.size[1]}  {os.path.getsize(ruta)} bytes")
    except Exception as e:  # noqa: BLE001
        errores += 1
        print(f"FALLA {rel}: {e}")
base = os.path.join(RAIZ, "docs", "evidencias")
todas = {os.path.relpath(os.path.join(d, f), os.path.join(RAIZ, "docs")).replace(os.sep, "/")
         for d, _, fs in os.walk(base) for f in fs if f.endswith(".png") and not f.startswith("MANUAL-")}
sobran = sorted(todas - set(citadas))
print(f"\nCitadas: {len(citadas)} · con error: {errores} · PNG sin citar: {len(sobran)} {sobran}")
sys.exit(1 if errores else 0)
