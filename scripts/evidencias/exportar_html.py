"""Convierte docs/REPORTE_PRUEBAS.md y docs/ESTADO_PROYECTO.md a HTML para verlos
en el navegador con las imágenes (rutas relativas a docs/, sin copiar nada).

Uso: python scripts/evidencias/exportar_html.py   (requiere: pip install markdown)
Genera docs/REPORTE_PRUEBAS.html y docs/ESTADO_PROYECTO.html.
"""
import html
import os
import re

import markdown

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(RAIZ, "docs")

CSS = """
:root { --fondo:#f7f7f8; --papel:#ffffff; --texto:#1f2328; --suave:#57606a; --borde:#d0d7de; --acento:#d4001a; --codigo:#f3f4f6; }
@media (prefers-color-scheme: dark) { :root { --fondo:#0d1117; --papel:#161b22; --texto:#e6edf3; --suave:#9da7b3; --borde:#30363d; --acento:#ff5a6a; --codigo:#1f2630; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--fondo); color:var(--texto); font:16px/1.6 "Segoe UI", system-ui, -apple-system, sans-serif; }
.barra { position:sticky; top:0; z-index:5; background:var(--papel); border-bottom:1px solid var(--borde); padding:10px 16px; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
.barra b { color:var(--acento); }
.barra a { color:var(--texto); text-decoration:none; font-size:13px; white-space:nowrap; }
.barra a:hover { text-decoration:underline; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 80px; background:var(--papel); }
h1 { color:var(--acento); margin-top:0; }
h2, h3 { scroll-margin-top:64px; }
h2 { border-bottom:2px solid var(--borde); padding-bottom:4px; margin-top:48px; }
h3 { margin-top:40px; padding:6px 10px; background:var(--codigo); border-left:4px solid var(--acento); border-radius:4px; }
table { border-collapse:collapse; width:100%; margin:12px 0; font-size:14px; display:block; overflow-x:auto; }
th, td { border:1px solid var(--borde); padding:6px 8px; vertical-align:top; text-align:left; }
th { background:var(--codigo); }
code { background:var(--codigo); padding:1px 4px; border-radius:4px; font-size:13px; }
pre { background:var(--codigo); padding:12px; border-radius:6px; overflow-x:auto; }
pre code { padding:0; }
img { max-width:100%; height:auto; border:1px solid var(--borde); border-radius:6px; display:block; margin:12px auto 4px; cursor:zoom-in; }
img.grande { position:fixed; inset:0; margin:auto; max-width:96vw; max-height:96vh; z-index:20; cursor:zoom-out; box-shadow:0 0 0 100vmax rgba(0,0,0,.75); }
blockquote { margin:12px 0; padding:8px 16px; border-left:4px solid #e3b341; background:var(--codigo); }
p em { color:var(--suave); }
"""


def convertir(nombre_md, titulo):
    ruta = os.path.join(DOCS, nombre_md)
    texto = open(ruta, encoding="utf-8").read()
    cuerpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists", "toc"])
    secciones = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', cuerpo)
    def corto(t):
        t = re.sub("<[^>]+>", "", t)
        palabras = t.split()
        return " ".join(palabras[:3]) + ("…" if len(palabras) > 3 else "")
    indice = " ".join(f'<a href="#{i}" title="{html.escape(re.sub("<[^>]+>", "", t))}">{html.escape(corto(t))}</a>' for i, t in secciones)
    pagina = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title><style>{CSS}</style></head>
<body><nav class="barra"><b>{html.escape(titulo)}</b>{indice}</nav><main>{cuerpo}</main>
<script>document.querySelectorAll('main img').forEach(function (i) {{
  i.loading = 'lazy'; i.addEventListener('click', function () {{ i.classList.toggle('grande'); }}); }});</script>
</body></html>"""
    destino = os.path.join(DOCS, nombre_md.replace(".md", ".html"))
    with open(destino, "w", encoding="utf-8") as f:
        f.write(pagina)
    print("generado", destino)


convertir("REPORTE_PRUEBAS.md", "Reporte de pruebas · ScribeTracker")
convertir("ESTADO_PROYECTO.md", "Estado del proyecto · ScribeTracker")
