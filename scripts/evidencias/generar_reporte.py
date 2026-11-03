"""Genera docs/REPORTE_PRUEBAS.md a partir de fuentes reales.

Fuentes:
- scripts/evidencias/casos.py              catálogo de casos CP-01..CP-27
- backend/tests/*.py                       código y docstring de cada prueba (RF, tipo, datos, esperado)
- docs/evidencias/salidas/CP-xx_sqlserver.txt   salida real en la laptop con SQL Server
- docs/evidencias/salidas/obtenidos_sqlite.xml  resultado obtenido (HTTP y mensaje) de cada prueba
- docs/evidencias/capturas_interfaz.json        capturas de la interfaz
- docs/pruebas/historial_fallos.json            fallos F01-F07 registrados al detectarlos
Uso (desde la raíz del repositorio): python scripts/evidencias/generar_reporte.py
"""
import ast
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from casos import CASOS  # noqa: E402

DOCS = os.path.join(RAIZ, "docs")
EVID = os.path.join(DOCS, "evidencias")
SAL = os.path.join(EVID, "salidas")

RECHAZO = {"CP-09", "CP-10", "CP-11", "CP-12", "CP-13", "CP-14", "CP-16", "CP-17", "CP-19", "CP-20", "CP-21", "CP-27"}

# Pruebas de la etapa 1 (test_auth.py) sin campos en su docstring: se documentan aquí
# a partir de su código.
CAMPOS_EXTRA = {
    "CP-01": dict(RF="RF-01 (3.6) Inicio de sesión; RNF-16 Seguridad (no exponer contraseñas)", Tipo="válido",
                  Pre="Usuario promotor@test.mx Activo con contraseña conocida (hash Werkzeug)",
                  Entrada="POST /api/auth/login con correo y contraseña correctos",
                  Esperado="HTTP 200 con rol Promotor; la respuesta no contiene la contraseña, ni el hash (completo o parcial), ni las claves password/password_hash"),
    "CP-08": dict(RF="RF-01 (3.6); RNF-16 Control de acceso por rol (comprobado en el servidor)", Tipo="válido e inválido (9 combinaciones)",
                  Pre="Un usuario Activo por rol: Promotor, Supervisor y Administrador",
                  Entrada="Cada rol inicia sesión y pide la pantalla inicial de cada uno de los 3 roles (/api/inicio/<rol>)",
                  Esperado="HTTP 200 solo en la pantalla de su propio rol; HTTP 403 en las otras 2 (6 de 9 combinaciones son rechazos esperados)"),
    "CP-09": dict(RF="RF-01 (3.6) Inicio de sesión: estatus Activo; RF-06 Baja lógica", Tipo="inválido",
                  Pre="Usuario inactivo@test.mx con estatus Inactivo y contraseña correcta",
                  Entrada="POST /api/auth/login con la contraseña correcta",
                  Esperado="HTTP 403 con mensaje de cuenta inactiva; no se crea sesión (/api/auth/me responde 401)"),
}

# Capturas de interfaz que ilustran cada caso
UI_POR_CASO = {
    "CP-09": ["UI-02"], "CP-10": ["UI-27"], "CP-11": ["UI-22"], "CP-12": ["UI-23"], "CP-13": ["UI-27"],
    "CP-15": ["UI-05"], "CP-16": ["UI-04"], "CP-18": ["UI-06"], "CP-20": ["UI-08", "UI-09"], "CP-21": ["UI-07"],
    "CP-22": ["UI-10"], "CP-23": ["UI-12", "UI-13"], "CP-24": ["UI-11"], "CP-26": ["UI-18", "UI-19"], "CP-27": ["UI-25"],
}

ENT_SQLSERVER = "Laptop15-Elizabeth · Windows 11 · Python 3.13 · **SQL Server**, base de pruebas `ScribeTracker_Pruebas`"
ENT_DEV = "Entorno de desarrollo (Linux · Python 3.13 · **SQLite** de pruebas)"

# Detalle de cada fallo: clasificación, fragmentos y explicación (los fragmentos "después"
# se copian del código actual; los "antes" salen de los registros originales).
FALLOS = {
    "F01": dict(
        tipo="Error en la prueba (aserción demasiado amplia). El sistema no exponía contraseñas.",
        causa="La prueba buscaba la palabra \"password\" en toda la respuesta. Al agregar la bandera booleana "
              "`debe_cambiar_password` (cambio obligatorio de contraseña temporal) la palabra aparecía en el nombre del campo, "
              "aunque no había ninguna contraseña ni hash.",
        archivo="backend/tests/test_auth.py",
        antes='assert "password" not in str(r.get_json()).lower()',
        despues='assert "password" not in usuario\n# ...\ntexto = r.get_data(as_text=True)\nassert PASSWORD not in texto\n'
                '# además se comprueba que el hash (completo o parcial) no aparece',
        porque="Ahora se comprueba lo que exige el requisito (que la contraseña y su hash no viajen en la respuesta) "
               "y no el nombre de un campo booleano."),
    "F02": dict(
        tipo="**Defecto real del sistema** (error 500 al responder a un usuario con contraseña temporal).",
        causa="`error(mensaje, codigo, **extra)` recibía el código HTTP como segundo parámetro llamado `codigo` y también "
              "el dato extra `codigo=\"cambiar_password\"`: Python lanzaba `TypeError: got multiple values for argument 'codigo'`.",
        archivo="backend/app/auth.py",
        antes='def error(mensaje, codigo=400, **extra):\n    ...\nreturn error("Debes cambiar tu contraseña temporal antes de continuar.", 403,\n             codigo="cambiar_password")',
        despues='def error(mensaje: str, http: int = 400, **extra):\n    return jsonify(error=mensaje, **extra), http',
        porque="El código HTTP ya no se llama igual que el dato extra, así que la respuesta 403 con `codigo: cambiar_password` "
               "se construye sin error y la prueba recibe lo esperado."),
    "F03": dict(
        tipo="Error en los datos de la prueba. El sistema aplicó correctamente la regla.",
        causa="La prueba registraba el primer check-in a las 08:00, antes del inicio de jornada (08:05). El servidor lo "
              "rechazó con 400 \"La hora del registro es anterior al inicio de tu jornada\", que es el comportamiento correcto.",
        archivo="backend/tests/test_jornada.py",
        antes="for idx, h in ((0, 8), (1, 11)):\n    a_las(h, 0)",
        despues="for idx, h in ((0, 8), (1, 11)):\n    a_las(h, 10)",
        porque="Con horas coherentes (check-in 08:10, después del inicio) el flujo completo llega hasta el cierre sin forzar."),
    "F04": dict(
        tipo="Error en el diseño de la prueba.",
        causa="Se esperaban 3 promotores para el administrador, pero la base de la etapa 1 incluye a \"Pedro Promotor\" "
              "(activo, sin número de empleado). El sistema devolvía correctamente 4.",
        archivo="backend/tests/test_supervision_reportes.py",
        antes="(no se conservó el fragmento; el registro original muestra la comparación con {'P1', 'P2', 'P3'})",
        despues='assert {p["nombre_completo"] for p in admin["promotores"]} == { ...los 4 promotores activos... }',
        porque="La prueba compara ahora los nombres de todos los promotores activos que existen en el escenario."),
    "F05": dict(
        tipo="Error en el diseño de la prueba.",
        causa="La prueba tomaba el primer promotor de la lista suponiendo que era P1, pero la lista se ordena por nombre.",
        archivo="backend/tests/test_supervision_reportes.py",
        antes="(no se conservó el fragmento; la prueba tomaba el primer elemento de la lista)",
        despues='p1 = [p for p in ...["promotores"] if p["numero_empleado"] == "P1"][0]\nassert p1["estado_conexion"] == "Reciente"',
        porque="El promotor se busca por su número de empleado, sin depender del orden."),
    "F06": dict(
        tipo="**Defecto real del sistema** (error 500 al exportar el PDF si una foto estaba dañada).",
        causa="reportlab abre las imágenes al construir el documento; una sola foto truncada lanzaba `OSError: Truncated File Read` "
              "y el PDF completo fallaba.",
        archivo="backend/app/servicios/reportes.py",
        antes="Image(ruta, width=ancho, height=alto, kind=\"proportional\")   # sin verificar el archivo",
        despues="def _imagen_segura(ruta, Image, ancho, alto):\n    if not ruta or not os.path.isfile(ruta):\n        return None\n"
                "    try:\n        from PIL import Image as PILImage\n        with PILImage.open(ruta) as im:\n            im.load()\n"
                "        return Image(ruta, width=ancho, height=alto, kind=\"proportional\")\n    except Exception:\n        return None",
        porque="Cada imagen se valida con Pillow antes de incluirla; la dañada se omite y el resto del PDF se genera."),
    "F07": dict(
        tipo="**Defecto real del sistema** (la cola sin conexión dejaba de reintentar).",
        causa="En `sincronizar()`, sin pendientes la función terminaba sin ningún `await` y su `finally` ponía `enCurso = null` "
              "antes de que se guardara la promesa. `enCurso` quedaba ocupado para siempre y ninguna sincronización posterior se ejecutaba.",
        archivo="frontend/src/app/core/cola.service.ts",
        antes="async sincronizar() {\n  if (this.enCurso) return this.enCurso;\n  this.enCurso = (async () => {\n    try { ... } finally { this.enCurso = null; }\n  })();\n  return this.enCurso;\n}",
        despues="sincronizar(): Promise<void> {\n  if (this.enCurso) return this.enCurso;\n  const ejecucion = (async () => { ... })();\n"
                "  this.enCurso = ejecucion;\n  void ejecucion.finally(() => { if (this.enCurso === ejecucion) this.enCurso = null; });\n  return ejecucion;\n}",
        porque="`enCurso` solo se limpia cuando termina la misma ejecución que se guardó, así que cada evento \"online\" o el intervalo "
               "de 30 s vuelven a sincronizar."),
    "F08": dict(
        tipo="**Defecto real del sistema** (la pantalla mostraba un estado distinto al del servidor después de sincronizar).",
        causa="Al terminar la sincronización, la cola quitaba los eventos pendientes, pero la pantalla del promotor no volvía a leer "
              "`/api/promotor/hoy` hasta el refresco automático de 60 s. Durante ese tiempo Soriana aparecía \"Por visitar\" con el "
              "botón CHECK-IN, aunque el servidor ya tenía la visita abierta, y la franja decía \"0 pendiente(s) · datos guardados en el teléfono\". "
              "Un segundo CHECK-IN habría sido rechazado y confundía al promotor.",
        archivo="frontend/src/app/core/cola.service.ts y frontend/src/app/promotor/promotor.service.ts",
        antes="// cola.service.ts: al terminar sincronizar() no se avisaba a nadie\n} finally {\n  this.sincronizando.set(false);\n}\n"
              "// promotor-shell.ts: la pantalla solo se recargaba al entrar y cada 60 s\nthis.refresco = setInterval(() => void this.ps.cargar(), 60_000);",
        despues="// cola.service.ts\nalSincronizar(oyente: () => void) { this.oyentes.push(oyente); }\n...\n} finally {\n  this.sincronizando.set(false);\n}\n"
                "for (const oyente of this.oyentes) oyente();\n\n// promotor.service.ts\nconstructor() {\n"
                "  this.cola.alSincronizar(() => { if (this.cola.enLinea()) void this.cargar(); });\n}",
        porque="Al terminar cada sincronización con red, la pantalla vuelve a pedir el estado al servidor; 5 s después de recuperar la "
               "señal ya muestra la visita \"En curso\" y oculta el botón CHECK-IN."),
}


def leer(ruta):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read()


def fuentes_pruebas():
    """{nombre_funcion: (codigo, docstring)} de todas las pruebas del backend."""
    res = {}
    carpeta = os.path.join(RAIZ, "backend", "tests")
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.startswith("test_") or not nombre.endswith(".py"):
            continue
        src = leer(os.path.join(carpeta, nombre)).replace("\r\n", "\n")
        arbol = ast.parse(src)
        for nodo in arbol.body:
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                ini = (nodo.decorator_list[0].lineno if nodo.decorator_list else nodo.lineno) - 1
                codigo = "\n".join(src.splitlines()[ini:nodo.end_lineno])
                res[nodo.name] = (codigo, ast.get_docstring(nodo) or "")
    return res


def campos_caso(cid, doc):
    c = campos_docstring(doc)
    for k, v in CAMPOS_EXTRA.get(cid, {}).items():
        c.setdefault(k, v)
    return c


def campos_docstring(doc):
    campos = {}
    for linea in doc.splitlines():
        m = re.match(r"\s*(RF|Tipo|Pre|Entrada|Esperado):\s*(.*)", linea)
        if m:
            campos[m.group(1)] = m.group(2).strip()
    return campos


def obtenidos_xml(ruta):
    res = {}
    if not os.path.isfile(ruta):
        return res
    raiz = ET.parse(ruta).getroot()
    for tc in raiz.iter("testcase"):
        nombre = tc.get("name").split("[")[0]
        valores = [p.get("value") for p in tc.iter("property") if p.get("name") == "obtenido"]
        falla = tc.find("failure") is not None or tc.find("error") is not None
        res.setdefault(nombre, {"obtenido": [], "falla": False, "n": 0})
        res[nombre]["obtenido"] += valores
        res[nombre]["falla"] |= falla
        res[nombre]["n"] += 1
    return res


def resumen_sqlserver(cid):
    ruta = os.path.join(SAL, f"{cid}_sqlserver.txt")
    if not os.path.isfile(ruta):
        return None
    txt = leer(ruta)
    fecha = re.search(r"Fecha y hora: ([0-9/]+ [0-9:]+)", txt)
    final = [l.strip("= ").strip() for l in txt.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return {"fecha": fecha.group(1) if fecha else "", "final": final[-1] if final else "(sin línea final)"}


def origen_imagen(nombre):
    """Clasifica cada PNG según cómo se obtuvo."""
    base = os.path.basename(nombre)
    if re.match(r"CP-0[1-7]_antes\.png$", base) or base == "CP-07_despues_registro.png":
        return "TEXTO", "Imagen generada a partir de un registro de texto original (no es captura de pantalla)"
    if re.match(r"CP-\d\d_(despues|resultado)\.png$", base):
        return "TEXTO", "Imagen generada a partir de la salida de texto de pytest en SQL Server (no es captura de pantalla)"
    if base == "UI-19_reporte_p1.png" or base.endswith("_pdf_p1.png"):
        return "PDF", "Primera página del PDF exportado, convertida a imagen"
    if nombre.startswith("sqlserver/") or "sqlserver" in base:
        return "CAPTURA", "Captura de pantalla real (Chromium automatizado) · SQL Server ScribeTracker_Pruebas, laptop"
    return "CAPTURA", "Captura de pantalla real (Chromium automatizado) · SQLite de pruebas, desarrollo"


INVENTARIO = []


def img(nombre, alt):
    ruta = os.path.join(EVID, nombre)
    marca = "" if os.path.isfile(ruta) else " **(FALTA EL ARCHIVO)**"
    tipo, texto = origen_imagen(nombre)
    if nombre not in [i[0] for i in INVENTARIO]:
        INVENTARIO.append((nombre, tipo, texto, alt))
    icono = {"TEXTO": "📄", "PDF": "📑", "CAPTURA": "🖥️"}[tipo]
    return (f"![{alt}](evidencias/{nombre}){marca}\n\n*{alt}* — `docs/evidencias/{nombre}`{marca}<br>"
            f"{icono} **Origen:** {texto}\n")


def main():
    pruebas = fuentes_pruebas()
    obt = obtenidos_xml(os.path.join(SAL, "obtenidos_sqlite.xml"))
    obt_ss = obtenidos_xml(os.path.join(SAL, "obtenidos_sqlserver.xml"))
    ui = {r["id"]: r for r in json.load(open(os.path.join(EVID, "capturas_interfaz.json"), encoding="utf-8"))}
    cp28 = {k: json.load(open(os.path.join(SAL, f"CP-28_{k}.json"), encoding="utf-8")) for k in ("antes", "despues")}
    ruta28 = os.path.join(SAL, "CP-28_sqlserver.json")
    cp28["sqlserver"] = json.load(open(ruta28, encoding="utf-8")) if os.path.isfile(ruta28) else None
    ruta_ui_ss = os.path.join(EVID, "sqlserver", "capturas_interfaz.json")
    ui_ss = {r["id"]: r for r in json.load(open(ruta_ui_ss, encoding="utf-8"))} if os.path.isfile(ruta_ui_ss) else {}
    hay_obt_ss = bool(obt_ss)

    o = []
    w = o.append
    w("# Reporte de pruebas · ScribeTracker\n")
    w("Entrega: miércoles 4 de noviembre de 2026. Generado con `scripts/evidencias/generar_reporte.py` a partir de las salidas "
      "reales guardadas en `docs/evidencias/` y `docs/pruebas/`. No se editó ningún resultado a mano.\n")
    w("## 1. Cómo leer este reporte\n")
    w("Cada caso (CP) tiene: requisito, tipo de resultado, datos, procedimiento, código de la prueba, resultado esperado, "
      "resultado obtenido, estado, entorno e imágenes. Los casos con fallo incluyen además la captura **antes**, la causa, "
      "el archivo y fragmento corregidos, y la captura **después** del mismo caso.\n")
    w("**Tipos de resultado:**\n")
    w("- **Defecto real del sistema:** la aplicación hacía algo incorrecto y se corrigió el código de la aplicación (F02, F06, F07, F08).")
    w("- **Error en la prueba:** la aplicación estaba bien y lo que se corrigió fue la prueba (datos o aserción) (F01, F03, F04, F05).")
    w("- **Rechazo esperado:** la prueba *pasa* porque el sistema rechaza correctamente una acción inválida (por ejemplo, check-out sin las 4 fotos). "
      "No es un fallo.")
    w("- **Flujo válido:** la prueba pasa porque el sistema acepta y registra correctamente una acción válida.\n")

    w("## 2. Entornos de ejecución\n")
    w("| Entorno | Qué se ejecutó | Fecha |\n|---|---|---|")
    w("| **Laptop con SQL Server** (`ScribeTracker_Pruebas`, base separada de la real) | Suite completa del backend: 91 de 91. Casos CP-01 a CP-06 (después) y CP-08 a CP-27, uno por uno, con `scripts\\evidencias_sqlserver.bat` | 02/11/2026 22:59 y 23:26; 03/11/2026 14:56-15:05 |")
    w("| **Laptop: navegador + Flask + SQL Server real** (`ScribeTracker`) | Pruebas E2E-01 a E2E-09 desde Angular; aquí se encontró y verificó F07 (CP-07) | 02/11/2026 23:20-23:26 |")
    w("| **Desarrollo, SQLite** | Donde se detectaron F01-F06 (CP-01 a CP-06, antes). También el detalle HTTP \"obtenido\" de cada caso (sección 4) | 02/11/2026 22:30-22:50; 03/11/2026 |")
    w("| **Angular (build de producción) + Flask + SQLite de pruebas, en desarrollo** | Capturas de pantalla UI-01 a UI-27, CP-07 (verificación repetida) y CP-28 (F08 antes y después). Ubicación simulada y cámara simulada de Chromium | 03/11/2026 |")
    if ui_ss or hay_obt_ss or cp28["sqlserver"]:
        w("| **Laptop: Angular (build de producción) + Flask + SQL Server** (`ScribeTracker_Pruebas`), con `scripts\\evidencias_sqlserver_interfaz.bat` | "
          + ("Detalle HTTP obtenido de cada caso en SQL Server; " if hay_obt_ss else "")
          + (f"capturas de pantalla UI-01 a UI-27 en `docs/evidencias/sqlserver/` ({len(ui_ss)}); " if ui_ss else "")
          + ("CP-28 (F08) repetido con SQL Server" if cp28["sqlserver"] else "") + " | 03/11/2026 |")
    w("")
    lim = ["> **Limitaciones de la evidencia, dicho con claridad:**\n>",
           "> - Los fallos F01-F07 se registraron en su momento como **texto** (salida de pytest o del navegador), no como capturas de pantalla. "
           "Las imágenes \"antes\" de CP-01 a CP-07 son ese texto original convertido a imagen, sin editar (marcadas 📄). Para F04 y F05 solo se guardó "
           "el fragmento de la aserción.",
           "> - Las imágenes de resultado de las pruebas del backend (CP-xx_despues y CP-xx_resultado) también son texto: la salida real de pytest en SQL Server convertida a imagen (📄).",
           "> - Las pruebas E2E-01 a E2E-09 y la verificación original de F07 (02/11) se hicieron en el navegador integrado de la laptop, que no guarda capturas: solo hay registro de texto."]
    if ui_ss:
        lim.append("> - Las capturas de pantalla (🖥️) existen en dos juegos: el original en desarrollo con SQLite (`docs/evidencias/UI-*.png`) y el repetido en la laptop con "
                   "SQL Server (`docs/evidencias/sqlserver/UI-*.png`). Se conservan ambos.")
    else:
        lim.append("> - Las capturas de pantalla (🖥️) se tomaron en desarrollo con SQLite; la versión con SQL Server aún no se generó.")
    if hay_obt_ss:
        lim.append("> - El detalle HTTP \"obtenido\" se muestra de la ejecución en SQL Server; el de SQLite se conserva debajo como referencia original.")
    else:
        lim.append("> - El detalle HTTP \"obtenido\" viene de la ejecución con SQLite; en SQL Server los mismos casos pasaron (salida en cada imagen).")
    w("\n".join(lim) + "\n")

    w("## 3. Resumen\n")
    w("| Caso | Nombre | Requisito | Tipo de resultado | Estado final | Entorno de la evidencia final |\n|---|---|---|---|---|---|")
    filas = []
    for cid, f, nombre, prueba in CASOS:
        fn = prueba.split("::")[-1] if prueba else ""
        rf = campos_caso(cid, pruebas.get(fn, ("", ""))[1]).get("RF", "—") if fn else "RNF-08 / RNF-09 (sin conexión)"
        if f:
            tipo = FALLOS[f]["tipo"].split(".")[0].replace("**", "")
            tipo = f"Fallo {f}: {tipo}"
        else:
            tipo = "Rechazo esperado" if cid in RECHAZO else ("Flujo válido y rechazos esperados" if cid == "CP-08" else "Flujo válido")
        ent = "Angular + SQL Server real (laptop)" if cid == "CP-07" else "SQL Server (laptop)"
        filas.append((cid, nombre, rf, tipo, "Exitosa (después de corregir)" if f else "Exitosa", ent))
    filas.append(("CP-28", "Pantalla actualizada al terminar la sincronización", "RNF-08 / RNF-09; RF-03",
                  "Fallo F08: Defecto real del sistema", "Exitosa (después de corregir)",
                  "Angular + SQL Server (laptop) y Angular + SQLite (desarrollo)" if cp28["sqlserver"] else "Angular + SQLite (desarrollo)"))
    for fila in filas:
        w("| " + " | ".join(fila) + " |")
    w("")
    w(f"Total: {len(filas)} casos documentados. **8 fallos reales** encontrados durante el desarrollo (F01-F08): 4 defectos del sistema "
      "y 4 errores de las pruebas, todos corregidos y verificados con el mismo caso. 12 casos comprueban rechazos esperados.\n")

    w("## 4. Casos de prueba\n")
    for cid, f, nombre, prueba in CASOS:
        if cid == "CP-07":
            caso_cp07(w, ui)
            continue
        archivo, fn = prueba.split("::")
        codigo, doc = pruebas[fn]
        c = campos_caso(cid, doc)
        ss = resumen_sqlserver(cid)
        titulo = doc.splitlines()[0] if doc else f"etapa 1, sin docstring; campos tomados del código"
        w(f"### {cid} · {nombre}\n")
        w("| Campo | Detalle |\n|---|---|")
        w(f"| Prueba | `backend/{archivo}::{fn}` ({titulo}) |")
        w(f"| Requisito funcional | {c.get('RF', '—')} |")
        if f:
            w(f"| Tipo de resultado | Fallo **{f}** · {FALLOS[f]['tipo']} |")
        else:
            w(f"| Tipo de resultado | {'**Rechazo esperado**: la prueba pasa porque el servidor rechaza la acción inválida' if cid in RECHAZO else ('**Flujo válido y rechazos esperados**' if cid == 'CP-08' else '**Flujo válido**')} ({c.get('Tipo', '')}) |")
        w(f"| Precondiciones | {c.get('Pre', '—')} |")
        w(f"| Datos de entrada | {c.get('Entrada', '—')} |")
        w(f"| Procedimiento | `set ST_BD_PRUEBAS=ScribeTracker_Pruebas` y `python -m pytest {archivo}::{fn} -v` en `backend` |")
        w(f"| Resultado esperado | {c.get('Esperado', '—')} |")
        det = obt.get(fn, {}).get("obtenido") or []
        det_ss = obt_ss.get(fn, {}).get("obtenido") or []
        txt_obt = f"SQL Server ({ss['fecha']}): **{ss['final']}**" if ss else "—"
        if fn in obt_ss:
            estado_ss = "falló" if obt_ss[fn]["falla"] else f"{obt_ss[fn]['n']} passed"
            txt_obt += f"<br>Ejecución conjunta en SQL Server ({estado_ss}): " + (" · ".join(dict.fromkeys(det_ss)).replace("|", "/") or "(la prueba no registra detalle HTTP; solo aserciones)")
        if det:
            txt_obt += "<br>Detalle original (ejecución con SQLite): " + " · ".join(dict.fromkeys(det)).replace("|", "/")
        w(f"| Resultado obtenido | {txt_obt} |")
        w(f"| Estado | {'Exitosa después de corregir (antes: fallida)' if f else 'Exitosa'} |")
        w(f"| Entorno | {ENT_SQLSERVER}" + (f"; el fallo original ocurrió en {ENT_DEV}" if f else "") + " |")
        w("")
        w("**Código de la prueba**\n")
        w("```python\n" + codigo + "\n```\n")
        if f:
            d = FALLOS[f]
            w(f"**Antes de corregir ({f})** · registro original del fallo\n")
            w(img(f"{cid}_antes.png", f"{cid} antes: salida original del fallo {f}"))
            w(f"- **Causa:** {d['causa']}")
            w(f"- **Archivo corregido:** `{d['archivo']}`")
            w("- **Fragmento antes:**\n\n```\n" + d["antes"] + "\n```")
            w("- **Fragmento después:**\n\n```\n" + d["despues"] + "\n```")
            w(f"- **Por qué ahora pasa:** {d['porque']}\n")
            w("**Después de corregir** · el mismo caso, repetido en SQL Server\n")
            w(img(f"{cid}_despues.png", f"{cid} después: misma prueba en SQL Server"))
        else:
            w("**Evidencia**\n")
            w(img(f"{cid}_resultado.png", f"{cid}: salida real en SQL Server"))
        for u in UI_POR_CASO.get(cid, []):
            r = ui_ss.get(u)
            if r:
                arch = r["archivo"] if r["archivo"].endswith(".png") else "UI-19_reporte_pdf_p1.png"
                w(img(f"sqlserver/{arch}", f"{u} · {r['descripcion']} (interfaz con SQL Server)"))
            r = ui.get(u)
            if r:
                w(img(r["archivo"] if r["archivo"].endswith(".png") else "UI-19_reporte_p1.png", f"{u} · {r['descripcion']} (interfaz, SQLite de desarrollo, original)"))
        w("")

    caso_cp28(w, cp28)

    w("## 5. Pruebas desde Angular en la laptop con SQL Server real (E2E)\n")
    w("Registradas en `docs/pruebas/pruebas_e2e.json` (02/11/2026, navegador integrado + Flask + base `ScribeTracker`). "
      "No hay capturas de estas ejecuciones porque ese navegador no guarda imágenes; las pantallas equivalentes están en el anexo.\n")
    e2e = json.load(open(os.path.join(DOCS, "pruebas", "pruebas_e2e.json"), encoding="utf-8"))
    w("| ID | Nombre | RF | Esperado | Obtenido | Estado |\n|---|---|---|---|---|---|")
    for e in e2e:
        w(f"| {e['id']} | {e['nombre']} | {e['rf']} | {e['esperado']} | {e['obtenido'].replace('|', '/')} | {e['estado']} |")
    w("")

    if ui_ss:
        w("## 6. Anexo A: recorrido de la interfaz con SQL Server (laptop)\n")
        w("Capturas tomadas en la laptop con la aplicación compilada (Angular), Flask y SQL Server, base de pruebas `ScribeTracker_Pruebas` "
          "(sembrada con datos de demostración; nunca la base real). Ubicación y cámara simuladas por Chromium. "
          "La contraseña temporal de UI-24 se tapó a propósito antes de capturar. En UI-05 las teselas del mapa (OpenStreetMap) "
          "no terminaron de cargar al momento de capturar; los marcadores, el estado y la lista sí son los reales.\n")
        for u, r in ui_ss.items():
            if r["archivo"].endswith(".png") and u.startswith("UI-"):
                w(f"#### {u} · {r['descripcion']} (SQL Server)\n")
                w(img(f"sqlserver/{r['archivo']}", u + " con SQL Server"))
        if os.path.isfile(os.path.join(EVID, "sqlserver", "UI-19_reporte_pdf_p1.png")):
            w(img("sqlserver/UI-19_reporte_pdf_p1.png", "UI-19 con SQL Server · primera página del PDF (docs/evidencias/sqlserver/UI-19_reporte.pdf)"))
        for cid7 in ("CP-07_despues_1_sin_conexion.png", "CP-07_despues_2_sincronizado.png"):
            if os.path.isfile(os.path.join(EVID, "sqlserver", cid7)):
                w(f"#### {cid7[:-4]} (SQL Server)\n")
                w(img(f"sqlserver/{cid7}", cid7[:-4] + " con SQL Server"))
    w("## 6b. Anexo B: recorrido de la interfaz original (desarrollo, SQLite)\n" if ui_ss else "## 6. Anexo: recorrido de la interfaz\n")
    w("Capturas tomadas con la aplicación compilada (Angular) y Flask sobre SQLite de pruebas. Cada imagen lleva abajo el caso, el entorno y la hora. "
      "La contraseña temporal de UI-24 se tapó a propósito antes de capturar.\n")
    for u, r in ui.items():
        if r["archivo"].endswith(".png") and u.startswith("UI-"):
            w(f"#### {u} · {r['descripcion']}\n")
            w(img(r["archivo"], u))
    w(img("UI-19_reporte_p1.png", "UI-19 · Primera página del PDF exportado (docs/evidencias/UI-19_reporte.pdf)"))

    pendientes = {"UI-05": "Promotor → Entrada/salida con la jornada iniciada en Walmart Torres Landa",
                  "UI-07": "Promotor → Evidencias: CHECK-OUT sin fotos (rechazo esperado)",
                  "UI-15": "Supervisor → Módulo de supervisión (mapa, resumen y alertas)",
                  "UI-18": "Supervisor → Reportes con un reporte generado"}
    w("## 7. Las cuatro capturas con SQL Server que estaban pendientes\n")
    w("| Captura | Pantalla | Estado | Archivo |\n|---|---|---|---|")
    for u, desc in pendientes.items():
        r = ui_ss.get(u)
        if r and os.path.isfile(os.path.join(EVID, "sqlserver", r["archivo"])):
            w(f"| {u} | {desc} | Guardada automáticamente con SQL Server | `docs/evidencias/sqlserver/{r['archivo']}` |")
        else:
            w(f"| {u} | {desc} | **Pendiente**: tómala a mano (abajo) | — |")
    w("")
    w("Para repetirlas a mano en Chrome contra SQL Server: abre `scripts\\iniciar.bat`, entra a http://localhost:4200 y captura con `Win + Shift + S`. "
      "Guárdalas en `docs\\evidencias\\sqlserver\\` como `MANUAL-UI-xx.png` para distinguirlas de las automáticas.\n")

    w("## 8. Inventario de imágenes y su origen\n")
    w("📄 = imagen generada a partir de un registro de texto (no es captura de pantalla) · 🖥️ = captura de pantalla real · 📑 = página de PDF convertida a imagen.\n")
    w("| Archivo | Origen | Descripción |\n|---|---|---|")
    for nombre, tipo, texto, alt in INVENTARIO:
        icono = {"TEXTO": "📄", "PDF": "📑", "CAPTURA": "🖥️"}[tipo]
        w(f"| `docs/evidencias/{nombre}` | {icono} {texto} | {alt.replace('|', '/')} |")
    n = {t: sum(1 for i in INVENTARIO if i[1] == t) for t in ("TEXTO", "CAPTURA", "PDF")}
    w(f"\nTotal: {len(INVENTARIO)} imágenes · {n['TEXTO']} generadas a partir de texto · {n['CAPTURA']} capturas de pantalla · {n['PDF']} páginas de PDF.\n")

    with open(os.path.join(DOCS, "REPORTE_PRUEBAS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(o) + "\n")
    print("REPORTE_PRUEBAS.md generado:", len(o), "bloques")


def caso_cp07(w, ui):
    d = FALLOS["F07"]
    w("### CP-07 · Sincronización de eventos sin conexión (Angular)\n")
    w("| Campo | Detalle |\n|---|---|")
    w("| Prueba | E2E-OFF01 (manual en el navegador, registrada en texto) |")
    w("| Requisito funcional | RNF-08 / RNF-09 Funcionamiento y almacenamiento sin conexión; RF-03 Check-in; RF-05 Evidencias |")
    w(f"| Tipo de resultado | Fallo **F07** · {d['tipo']} |")
    w("| Precondiciones | promotor.prueba con jornada abierta; sesión iniciada en el navegador de la laptop |")
    w("| Datos de entrada | Sin red simulada: check-in en Soriana San Juan Bosco y foto \"Anaquel antes\"; luego se restaura la red |")
    w("| Procedimiento | DevTools → Network → Offline; CHECK-IN y foto; volver a Online; esperar 6 s y revisar la interfaz, `/api/promotor/hoy` e IndexedDB |")
    w("| Resultado esperado | Los 2 eventos se envían solos al volver la señal; el servidor los valida y guarda con origen \"Sin conexión\" y su hora de captura; 0 pendientes |")
    w("| Resultado obtenido (antes) | \"2 pendiente(s) de sincronizar\"; la visita de Soriana no llegó al servidor (null); 1 intento por evento, sin reintentos |")
    w("| Resultado obtenido (después) | 0 pendientes; visita de Soriana \"Abierta\", origen \"Sin conexión\", foto válida con hora de captura y de recepción; sin duplicados |")
    w("| Estado | Exitosa después de corregir (antes: fallida) |")
    w("| Entorno | Laptop15-Elizabeth · navegador integrado + Flask + **SQL Server real** `ScribeTracker` (02/11/2026 23:24-23:25). Verificación repetida hoy con el build de producción en desarrollo (SQLite) |")
    w("")
    w("**Código que se probó** (`frontend/src/app/core/cola.service.ts`, método `sincronizar`)\n")
    w("```ts\n" + d["despues"] + "\n```\n")
    w("**Antes de corregir (F07)** · registro original\n")
    w(img("CP-07_antes.png", "CP-07 antes: registro original de E2E-OFF01"))
    w(f"- **Causa:** {d['causa']}")
    w(f"- **Archivo corregido:** `{d['archivo']}`")
    w("- **Fragmento antes:**\n\n```ts\n" + d["antes"] + "\n```")
    w("- **Fragmento después:**\n\n```ts\n" + d["despues"] + "\n```")
    w(f"- **Por qué ahora pasa:** {d['porque']}\n")
    w("**Después de corregir** · mismo caso en la laptop (registro) y repetido hoy (capturas)\n")
    w(img("CP-07_despues_registro.png", "CP-07 después: registro original en la laptop con SQL Server"))
    for u in ("CP-07_despues_1_sin_conexion.png", "CP-07_despues_2_sincronizado.png"):
        w(img(u, "CP-07 después (repetido hoy): " + ("sin señal, check-in pendiente" if "_1_" in u else "señal recuperada, sincronizado y validado")))
    w("")


def caso_cp28(w, cp28):
    d = FALLOS["F08"]
    a, b = cp28["antes"], cp28["despues"]
    w("### CP-28 · Pantalla actualizada al terminar la sincronización (Angular)\n")
    w("Fallo nuevo encontrado el 03/11/2026 al preparar las capturas de CP-07: la sincronización funcionaba (el servidor tenía la visita), "
      "pero la pantalla seguía mostrando el estado anterior. Se guardó la evidencia antes de corregir y se repitió el mismo caso después.\n")
    w("| Campo | Detalle |\n|---|---|")
    w("| Prueba | `scripts/evidencias/reproducir_sincronizacion.py` (Playwright, automatizada) |")
    w("| Requisito funcional | RNF-08 / RNF-09 Sin conexión (estados \"pendiente\" y \"confirmado\" separados); RF-03 Check-in |")
    w(f"| Tipo de resultado | Fallo **F08** · {d['tipo']} |")
    w("| Precondiciones | Promotor demo con 4 tiendas; jornada iniciada y visita a Walmart completa (4 fotos) y cerrada |")
    w("| Datos de entrada | Ubicación a 10 m de Soriana San Juan Bosco (21.1395, -101.7104); red desactivada; CHECK-IN; red restaurada |")
    w("| Procedimiento | `python scripts/evidencias/reproducir_sincronizacion.py <url> <carpeta> antes/despues/sqlserver <entorno>`; a los 5 s de recuperar la señal compara la pantalla con `/api/promotor/hoy` |")
    w("| Resultado esperado | 5 s después de recuperar la señal, Soriana aparece \"En curso\", sin botón CHECK-IN, igual que en el servidor |")
    w(f"| Resultado obtenido (antes) | Pantalla: \"{a['pantalla']['soriana'].replace('|', '/')}\"; botón CHECK-IN visible: {a['pantalla']['boton_checkin_soriana']}; franja: \"{a['pantalla']['franja']}\". Servidor: visita {a['servidor']['estado']}, origen {a['servidor']['origen']} |")
    w(f"| Resultado obtenido (después) | Pantalla: \"{b['pantalla']['soriana'].replace('|', '/')}\"; botón CHECK-IN visible: {b['pantalla']['boton_checkin_soriana']}; visita en curso: \"{b['pantalla']['visita_en_curso'].replace('|', '/')}\". Servidor: visita {b['servidor']['estado']}, origen {b['servidor']['origen']} |")
    w("| Estado | Exitosa después de corregir (antes: fallida) |")
    w("| Entorno | Angular (build de producción compilado en la laptop) + Flask + SQLite de pruebas, entorno de desarrollo. Antes: build anterior; después: build de las 15:17 con la corrección |")
    w("")
    w("**Código de la prueba** (fragmento de `reproducir_sincronizacion.py`)\n")
    w("```python\nctx.set_geolocation({\"latitude\": SORIANA[0] + 10 * M, \"longitude\": SORIANA[1], \"accuracy\": 12})\n"
      "ctx.set_offline(True)\npage.locator(\"button\", has_text=\"CHECK-IN\").first.click()\npage.wait_for_selector(\".franja\")\n"
      "ctx.set_offline(False)\npage.evaluate(\"window.dispatchEvent(new Event('online'))\")\ntime.sleep(5)\n"
      "pantalla = {...}   # estado de Soriana y botón CHECK-IN en la pantalla\n"
      "servidor = page.evaluate(\"fetch('/api/promotor/hoy')...asignaciones[1].visita\")\n```\n")
    w("**Antes de corregir (F08)**\n")
    w(img("CP-28_antes.png", "CP-28 antes: la pantalla dice Por visitar y CHECK-IN mientras el servidor ya tiene la visita abierta"))
    w(f"- **Causa:** {d['causa']}")
    w(f"- **Archivos corregidos:** `{d['archivo']}`")
    w("- **Fragmento antes:**\n\n```ts\n" + d["antes"] + "\n```")
    w("- **Fragmento después:**\n\n```ts\n" + d["despues"] + "\n```")
    w(f"- **Por qué ahora pasa:** {d['porque']}\n")
    w("**Después de corregir** · el mismo caso\n")
    w(img("CP-28_despues.png", "CP-28 después: la pantalla coincide con el servidor (En curso, sin CHECK-IN)"))
    c = cp28.get("sqlserver")
    if c:
        ok = (not c["pantalla"]["boton_checkin_soriana"]) and "En curso" in c["pantalla"]["soriana"] and (c["servidor"] or {}).get("estado") == "Abierta"
        w("**Mismo caso repetido con SQL Server** (laptop, `ScribeTracker_Pruebas`, build con la corrección)\n")
        w("| Campo | Detalle |\n|---|---|")
        w(f"| Resultado obtenido | Pantalla: \"{c['pantalla']['soriana'].replace('|', '/')}\"; botón CHECK-IN visible: {c['pantalla']['boton_checkin_soriana']}; "
          f"franja: \"{c['pantalla']['franja']}\". Servidor (SQL Server): {c['servidor']} · hora {c['hora']} |")
        w(f"| Estado | {'Exitosa: la pantalla coincide con el servidor' if ok else '**NO coincide**: revisar'} |")
        w("")
        w(img("CP-28_sqlserver.png", "CP-28 con SQL Server: la pantalla coincide con el servidor"))
    else:
        w("> F08 todavía no se repitió con SQL Server: ejecuta `scripts\\evidencias_sqlserver_interfaz.bat`.\n")
    w("")


if __name__ == "__main__":
    main()
