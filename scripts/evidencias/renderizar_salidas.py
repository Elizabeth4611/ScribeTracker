"""Convierte salidas de texto reales (pytest, registros originales) en PNG legibles.

Cada imagen muestra arriba el caso, el origen del texto y el entorno, y abajo el
texto tal cual, sin editar. Uso:
    python renderizar_salidas.py <lista.json> <carpeta_salida>
donde lista.json es [{"png": "CP-08_despues.png", "titulo": "...", "origen": "...",
"entorno": "...", "archivo": "ruta/al/texto.txt", "estado": "PASA|FALLA|..."}, ...]
"""
import html
import json
import re
import sys

from playwright.sync_api import sync_playwright

COLORES = {"PASA": "#16a34a", "FALLA": "#dc2626", "PASA · RECHAZO ESPERADO": "#2563eb"}


def resaltar(linea: str) -> str:
    t = html.escape(linea)
    if linea.startswith(("> set", "> python", "Fecha y hora", "Base de datos", "Carpeta")):
        return f'<span class="dato">{t}</span>'
    if re.search(r"\bPASSED\b|\bpassed\b", linea) and "failed" not in linea:
        return f'<span class="ok">{t}</span>'
    if re.search(r"FAILED|failed|Error|^E\s|^>", linea):
        return f'<span class="mal">{t}</span>'
    if linea.startswith(">") or linea.startswith("Fecha") or linea.startswith("Base"):
        return f'<span class="dato">{t}</span>'
    return t


def pagina(c: dict, texto: str) -> str:
    color = COLORES.get(c["estado"], "#6b7280")
    cuerpo = "\n".join(resaltar(l) for l in texto.rstrip().splitlines())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    body {{ margin:0; background:#0b1020; font-family: 'DejaVu Sans', Arial, sans-serif; }}
    .cab {{ background:#111827; color:#f9fafb; padding:14px 18px; border-bottom:3px solid {color}; }}
    .cab h1 {{ margin:0 0 4px; font-size:19px; }}
    .cab p {{ margin:2px 0; font-size:13px; color:#cbd5e1; }}
    .estado {{ display:inline-block; background:{color}; color:#fff; font-weight:bold; padding:2px 10px; border-radius:4px; margin-left:8px; font-size:13px; }}
    pre {{ margin:0; padding:14px 18px; color:#e5e7eb; font:13px/1.45 'DejaVu Sans Mono', Consolas, monospace; white-space:pre-wrap; word-break:break-word; }}
    .ok {{ color:#4ade80; }} .mal {{ color:#f87171; }} .dato {{ color:#fde68a; }}
    </style></head><body><div class="cab"><h1>{html.escape(c['titulo'])}<span class="estado">{html.escape(c['estado'])}</span></h1>
    <p>Origen: {html.escape(c['origen'])}</p><p>Entorno: {html.escape(c['entorno'])}</p></div>
    <pre>{cuerpo}</pre></body></html>"""


def main():
    casos = json.load(open(sys.argv[1], encoding="utf-8"))
    salida = sys.argv[2]
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        page = nav.new_page(viewport={"width": 1100, "height": 400}, device_scale_factor=1.5)
        for c in casos:
            texto = open(c["archivo"], encoding="utf-8", errors="replace").read()
            page.set_content(pagina(c, texto))
            page.screenshot(path=f"{salida}/{c['png']}", full_page=True)
            print("ok", c["png"])
        nav.close()


if __name__ == "__main__":
    main()
