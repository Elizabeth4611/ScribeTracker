"""Genera docs/pruebas/REGISTRO_PRUEBAS.md y registro_pruebas.csv.

Fuentes (solo ejecuciones reales):
- Docstrings y código de backend/tests/test_*.py (ID, requisito, tipo,
  precondiciones, entrada, resultado esperado y bloque de código).
- Resultados JUnit de docs/pruebas/resultados_*.xml (estado y resultado
  obtenido de cada ejecución).
- docs/pruebas/historial_fallos.json (fallos reales, causa y corrección).
- docs/pruebas/pruebas_e2e.json (pruebas de interfaz hechas en la laptop).

Uso:  python scripts/generar_registro_pruebas.py
"""
import ast
import csv
import json
import os
import xml.etree.ElementTree as ET

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS = os.path.join(RAIZ, "backend", "tests")
DOCS = os.path.join(RAIZ, "docs", "pruebas")

ENTORNOS = [
    ("resultados_windows_sqlserver.xml", "Laptop Windows · SQL Server (base ScribeTracker_Pruebas)"),
    ("resultados_windows_sqlite.xml", "Laptop Windows · SQLite en memoria"),
]


def leer_docstring(doc: str, nombre: str) -> dict:
    lineas = [l.strip() for l in (doc or "").strip().splitlines()]
    d = {"id": "", "titulo": nombre, "rf": "", "tipo": "", "pre": "", "entrada": "", "esperado": ""}
    if lineas and "·" in lineas[0]:
        d["id"], d["titulo"] = (x.strip() for x in lineas[0].split("·", 1))
    claves = {"RF:": "rf", "Tipo:": "tipo", "Pre:": "pre", "Entrada:": "entrada", "Esperado:": "esperado"}
    for l in lineas[1:]:
        for k, v in claves.items():
            if l.startswith(k):
                d[v] = l[len(k):].strip()
    return d


def pruebas_del_codigo():
    filas = []
    for archivo in sorted(f for f in os.listdir(TESTS) if f.startswith("test_") and f.endswith(".py")):
        ruta = os.path.join(TESTS, archivo)
        fuente = open(ruta, encoding="utf-8").read().replace("\r\n", "\n")
        arbol = ast.parse(fuente)
        lineas = fuente.splitlines()
        contador = 0
        for nodo in arbol.body:
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                contador += 1
                info = leer_docstring(ast.get_docstring(nodo) or "", nodo.name)
                if not info["id"]:
                    # Pruebas de la etapa 1 (autenticación) sin docstring estructurado.
                    info["id"] = f"AUT{contador:02d}"
                    info["titulo"] = nodo.name.replace("test_", "").replace("_", " ").capitalize()
                    info["rf"] = "RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16"
                    info["tipo"] = "etapa 1"
                    info["esperado"] = "Las aserciones del código se cumplen"
                codigo = "\n".join(lineas[nodo.lineno - 1: nodo.end_lineno])
                filas.append({**info, "archivo": f"backend/tests/{archivo}", "funcion": nodo.name,
                              "clase": f"tests.{archivo[:-3]}", "codigo": codigo})
    return filas


def resultados():
    res = {}
    for xml, entorno in ENTORNOS:
        ruta = os.path.join(DOCS, xml)
        if not os.path.exists(ruta):
            continue
        for tc in ET.parse(ruta).iter("testcase"):
            nombre = tc.get("name").split("[")[0]
            clave = (tc.get("classname"), nombre)
            fallo = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
            omit = tc.find("skipped")
            estado = "fallida" if fallo is not None else ("no ejecutada" if omit is not None else "exitosa")
            prop = tc.find("properties/property[@name='obtenido']")
            obtenido = prop.get("value") if prop is not None else ("Aserciones cumplidas" if estado == "exitosa" else "")
            if fallo is not None:
                obtenido = (fallo.get("message") or "")[:300]
            previo = res.setdefault(clave, {}).get(entorno)
            if previo and previo["estado"] == "fallida":
                continue
            casos = res[clave].setdefault(entorno, {"estado": estado, "obtenido": obtenido, "casos": 0, "tiempo": 0.0})
            casos["casos"] += 1
            casos["tiempo"] += float(tc.get("time") or 0)
            if estado == "fallida":
                casos.update(estado="fallida", obtenido=obtenido)
    return res


def main():
    filas = pruebas_del_codigo()
    res = resultados()
    fallos = json.load(open(os.path.join(DOCS, "historial_fallos.json"), encoding="utf-8"))
    e2e = json.load(open(os.path.join(DOCS, "pruebas_e2e.json"), encoding="utf-8"))

    total = len(filas)
    exitosas = {e: sum(1 for f in filas if res.get((f["clase"], f["funcion"]), {}).get(e, {}).get("estado") == "exitosa")
                for _, e in ENTORNOS}

    md = ["# Registro de pruebas · ScribeTracker", "",
          "Documento generado con `python scripts/generar_registro_pruebas.py` a partir del código de las pruebas "
          "y de los resultados reales (JUnit). No contiene resultados inventados.", "",
          "## Resumen", "",
          f"- Pruebas automáticas del backend: **{total}** funciones de prueba (algunas parametrizadas: la matriz de permisos ejecuta 9 casos).",
          ]
    for _, e in ENTORNOS:
        md.append(f"- {e}: **{exitosas[e]} de {total}** exitosas en la última ejecución.")
    md += [f"- Pruebas de interfaz de punta a punta en la laptop: **{len(e2e)}** (ver sección E2E).",
           f"- Fallos reales encontrados y corregidos: **{len(fallos)}** (ver Historial de fallos).", "",
           "Tipos: *válido* (datos correctos), *inválido* (datos incorrectos o estado incompatible), "
           "*no autorizado* (permisos o petición manipulada).", "",
           "Entornos:", "",
           "- **Laptop Windows · SQL Server**: Python 3.13, Flask, SQLAlchemy y SQL Server Express de la laptop; "
           "base de datos separada `ScribeTracker_Pruebas` (nunca la base real).",
           "- **Laptop Windows · SQLite**: las mismas pruebas con SQLite en memoria.",
           "- **Entorno de desarrollo (Linux, SQLite)**: donde se ejecutaron por primera vez y se detectaron F01-F06.",
           "", "## Historial de fallos y correcciones", ""]
    md.append("| ID | Prueba | Tipo de fallo | Causa | Archivo y cambio | Re-ejecución | Evidencia |")
    md.append("|---|---|---|---|---|---|---|")
    for f in fallos:
        md.append(f"| {f['id']} | {f['prueba']} | {f['clasificacion']} | {f['causa']} | `{f['archivo']}`: {f['cambio']} | "
                  f"{f['despues']} | `{f['evidencia_antes']}` / `{f['evidencia_despues']}` |")
    md += ["", "## Pruebas de interfaz (E2E) en la laptop", "",
           "Ejecutadas en el navegador integrado contra Flask + SQL Server real (base `ScribeTracker`) con los usuarios de prueba. "
           "La ubicación GPS y la cámara se simularon dentro de la página (equivalente a *Sensores* de Chrome DevTools), "
           "porque la laptop no está físicamente en las tiendas.", ""]
    md.append("| ID | Requisito | Procedimiento | Esperado | Obtenido | Estado |")
    md.append("|---|---|---|---|---|---|")
    for p in e2e:
        md.append(f"| {p['id']} | {p['rf']} | {p['procedimiento']} | {p['esperado']} | {p['obtenido']} | {p['estado']} |")

    md += ["", "## Detalle de pruebas automáticas", ""]
    for f in filas:
        r = res.get((f["clase"], f["funcion"]), {})
        md += [f"### {f['id']} · {f['titulo']}", "",
               f"- **Requisito / caso de uso:** {f['rf']}",
               f"- **Tipo:** {f['tipo']}",
               f"- **Precondiciones:** {f['pre'] or '—'}",
               f"- **Datos de entrada:** {f['entrada'] or '—'}",
               f"- **Procedimiento:** `cd backend` y `python -m pytest {f['archivo'].replace('backend/', '')}::{f['funcion']} -v`",
               f"- **Resultado esperado:** {f['esperado']}"]
        for _, e in ENTORNOS:
            x = r.get(e)
            if x:
                extra = f" ({x['casos']} casos)" if x["casos"] > 1 else ""
                md.append(f"- **Resultado obtenido · {e}:** {x['obtenido']}{extra} → **{x['estado'].upper()}**")
            else:
                md.append(f"- **Resultado obtenido · {e}:** no ejecutada")
        hist = [x["id"] for x in fallos if f["funcion"] in x.get("funciones", [])]
        if hist:
            md.append(f"- **Historial:** falló antes de la corrección {', '.join(hist)} (ver tabla de fallos).")
        md += ["- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.",
               "", "<details><summary>Código de la prueba</summary>", "", "```python", f["codigo"], "```", "", "</details>", ""]

    with open(os.path.join(DOCS, "REGISTRO_PRUEBAS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    with open(os.path.join(DOCS, "registro_pruebas.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Nombre", "Requisito", "Tipo", "Precondiciones", "Entrada", "Procedimiento", "Esperado"]
                   + [f"Obtenido ({e})" for _, e in ENTORNOS] + [f"Estado ({e})" for _, e in ENTORNOS] + ["Archivo"])
        for f in filas:
            r = res.get((f["clase"], f["funcion"]), {})
            w.writerow([f["id"], f["titulo"], f["rf"], f["tipo"], f["pre"], f["entrada"],
                        f"python -m pytest {f['archivo'].replace('backend/', '')}::{f['funcion']}", f["esperado"]]
                       + [r.get(e, {}).get("obtenido", "no ejecutada") for _, e in ENTORNOS]
                       + [r.get(e, {}).get("estado", "no ejecutada") for _, e in ENTORNOS] + [f["archivo"]])
        for p in e2e:
            w.writerow([p["id"], p["nombre"], p["rf"], "E2E interfaz", p.get("pre", ""), "", p["procedimiento"], p["esperado"],
                        p["obtenido"], "", p["estado"], "", "navegador (laptop)"])
    print(f"Registro generado: {total} pruebas automáticas, {len(e2e)} E2E, {len(fallos)} fallos documentados.")


if __name__ == "__main__":
    main()
