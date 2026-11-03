"""Capturas de la interfaz Angular (prueba de punta a punta automatizada).

Recorre la aplicación real (build de producción de Angular + API Flask) con
Playwright/Chromium y guarda PNG numerados en docs/evidencias/.
- Ubicación: se fija con la opción de geolocalización del navegador de
  pruebas (equivalente a "Sensores" de Chrome DevTools).
- Cámara: cámara de prueba de Chromium (--use-fake-device-for-media-stream).
- Sin conexión: modo offline del navegador de pruebas.
Cada imagen lleva una franja inferior con el caso, el entorno y la hora.
Uso: python capturas_interfaz.py <url_base> <carpeta_salida> <entorno>
"""
import json
import os
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

BASE, SALIDA, ENTORNO = sys.argv[1], sys.argv[2], sys.argv[3]
WALMART = (21.1458, -101.6893)
SORIANA = (21.1395, -101.7104)
M = 1 / 111_320
registro = []


def franja(page, cid, texto, completa=False):
    # En capturas de página completa la franja va al final del documento (no fija),
    # para que no tape contenido a mitad de la imagen.
    page.evaluate("""([cid, texto, entorno, hora, completa]) => {
        document.getElementById('__franja')?.remove();
        const d = document.createElement('div'); d.id = '__franja';
        d.style.cssText = (completa ? 'position:absolute;top:' + document.documentElement.scrollHeight + 'px;' : 'position:fixed;bottom:0;') +
          'left:0;right:0;z-index:99999;background:#111827;color:#fde68a;' +
          'font:12px/1.35 Consolas,monospace;padding:6px 10px;border-top:2px solid #f59e0b;white-space:pre-wrap';
        d.textContent = cid + ' · ' + texto + '\\n' + entorno + ' · ' + hora;
        document.body.appendChild(d);
    }""", [cid, texto, ENTORNO, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), completa])


def captura(page, cid, nombre, texto, completa=False):
    franja(page, cid, texto, completa)
    time.sleep(0.3)
    archivo = f"{cid}_{nombre}.png"
    page.screenshot(path=f"{SALIDA}/{archivo}", full_page=completa)
    avisos = page.eval_on_selector_all(".aviso", "els => els.map(e => e.innerText)")
    registro.append({"id": cid, "archivo": archivo, "descripcion": texto, "url": page.url.replace(BASE, ""),
                     "avisos": avisos, "hora": datetime.now().isoformat(timespec="seconds")})
    page.evaluate("document.getElementById('__franja')?.remove()")


def ultimo_aviso(page, timeout=12000):
    page.wait_for_selector(".aviso", timeout=timeout)
    time.sleep(0.4)
    return page.eval_on_selector_all(".aviso", "els => els.map(e => e.innerText)")[-1]


def limpiar_avisos(page):
    page.evaluate("document.querySelectorAll('.aviso').forEach(a => a.click())")
    time.sleep(0.3)


def boton(page, texto):
    return page.locator("button", has_text=texto).first


def login(page, correo, password=None):
    password = password or os.environ["ST_DEMO_PASSWORD"]
    page.goto(f"{BASE}/login")
    page.fill("input[type=email]", correo)
    page.fill("input[type=password]", password)
    page.click("button[type=submit]")


def foto(page, categoria, sin_promo=False):
    page.select_option("select", categoria)
    if sin_promo:
        page.check(".check input")
    boton(page, "CAPTURAR").click()
    boton(page, "ENVIAR").wait_for()
    limpiar_avisos(page)
    boton(page, "ENVIAR").click()
    return ultimo_aviso(page)


with sync_playwright() as pw:
    nav = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])

    # ---------------- Promotor (vista móvil) ----------------
    ctx = nav.new_context(viewport={"width": 430, "height": 900}, device_scale_factor=2, locale="es-MX",
                          geolocation={"latitude": SORIANA[0], "longitude": SORIANA[1], "accuracy": 12},
                          permissions=["geolocation", "camera"])
    page = ctx.new_page()

    page.goto(f"{BASE}/login")
    captura(page, "UI-01", "login", "Pantalla de inicio de sesión")
    login(page, "inactivo@demo.mx")
    page.wait_for_selector(".alerta")
    captura(page, "UI-02", "cuenta_inactiva", "Login de cuenta Inactiva: el servidor rechaza el acceso (CP-09)")
    login(page, "promotor@demo.mx")
    page.wait_for_selector(".mosaico")
    captura(page, "UI-03", "inicio_promotor", "Inicio del promotor (rol Promotor)")

    page.click("a[href='/promotor/jornada']")
    boton(page, "INICIAR JORNADA").wait_for()
    time.sleep(1)
    boton(page, "INICIAR JORNADA").click()
    ultimo_aviso(page)
    captura(page, "UI-04", "inicio_fuera_primera_tienda", "Ubicación en Soriana (tienda 2): inicio de jornada rechazado (CP-16)")

    ctx.set_geolocation({"latitude": WALMART[0] + 20 * M, "longitude": WALMART[1], "accuracy": 12})
    limpiar_avisos(page)
    boton(page, "INICIAR JORNADA").click()
    ultimo_aviso(page)
    page.wait_for_selector("text=CHECK-IN")
    captura(page, "UI-05", "jornada_iniciada", "A 20 m de Walmart (tienda 1): jornada iniciada, sin visita todavía (CP-15, CP-18)")

    limpiar_avisos(page)
    page.locator("button", has_text="CHECK-IN").first.click()
    ultimo_aviso(page)
    captura(page, "UI-06", "checkin", "Check-in independiente en Walmart Torres Landa (CP-18)")

    boton(page, "TOMAR FOTOS").click()
    page.wait_for_selector("video")
    time.sleep(1.5)
    limpiar_avisos(page)
    boton(page, "CHECK-OUT").click()
    ultimo_aviso(page)
    captura(page, "UI-07", "checkout_sin_fotos", "Check-out sin fotos: rechazo esperado con categorías faltantes (CP-21)")

    ctx.set_geolocation({"latitude": WALMART[0] + 400 * M, "longitude": WALMART[1], "accuracy": 12})
    foto(page, "Precios")
    captura(page, "UI-08", "foto_fuera_geocerca", "Foto de Precios a 400 m: se guarda pero NO cuenta (CP-20)")

    ctx.set_geolocation({"latitude": WALMART[0] + 10 * M, "longitude": WALMART[1], "accuracy": 12})
    for c in ("Anaquel antes", "Anaquel después", "Precios"):
        foto(page, c)
    foto(page, "Promociones", sin_promo=True)
    page.wait_for_selector(".galeria figure:nth-child(5)")
    time.sleep(1.5)
    captura(page, "UI-09", "cuatro_categorias", "Cuatro categorías válidas (Promociones como exhibición Scribe) y foto rechazada marcada", completa=True)

    limpiar_avisos(page)
    boton(page, "CHECK-OUT").click()
    ultimo_aviso(page)
    page.wait_for_url("**/promotor/jornada")
    time.sleep(1)
    captura(page, "UI-10", "checkout_jornada_abierta", "Check-out válido: la visita se cierra y la jornada sigue abierta (CP-22)")

    page.click("a[href='/promotor/pausas']")
    boton(page, "DESCANSO").wait_for()
    limpiar_avisos(page)
    boton(page, "DESCANSO").click()
    ultimo_aviso(page)
    time.sleep(3)
    captura(page, "UI-11", "pausa_activa", "Pausa de descanso con temporizador: seguimiento detenido (CP-24)")
    limpiar_avisos(page)
    boton(page, "FINALIZAR").click()
    ultimo_aviso(page)

    # Sin conexión (CP-07 / F07)
    page.click("a[href='/promotor']")
    page.click("a[href='/promotor/jornada']")
    page.wait_for_selector(".lista-tiendas")
    time.sleep(1)
    ctx.set_geolocation({"latitude": SORIANA[0] + 10 * M, "longitude": SORIANA[1], "accuracy": 12})
    ctx.set_offline(True)
    limpiar_avisos(page)
    page.locator("button", has_text="CHECK-IN").first.click()
    ultimo_aviso(page)
    page.wait_for_selector(".franja")
    captura(page, "CP-07", "despues_1_sin_conexion",
            "Sin conexión: el check-in queda PENDIENTE (no validado) y guardado en el teléfono")
    ctx.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    # Con la corrección F08 la pantalla vuelve a leer el servidor al terminar de sincronizar.
    page.wait_for_selector(".franja", state="detached", timeout=20000)
    page.reload()
    page.wait_for_selector(".tarjeta-oscura")
    time.sleep(1.5)
    servidor = page.evaluate("fetch('/api/promotor/hoy').then(r => r.json()).then(d => d.asignaciones[1].visita)")
    captura(page, "CP-07", "despues_2_sincronizado",
            f"Señal recuperada: sincronizado y validado por el servidor (origen {servidor['origen']}, check-in {servidor['checkin'][11:]})")

    # Visita de Soriana completa y cierre con pendientes
    boton(page, "TOMAR FOTOS").click()
    page.wait_for_selector("video")
    time.sleep(1.5)
    for c in ("Anaquel antes", "Anaquel después", "Precios", "Promociones"):
        foto(page, c)
    limpiar_avisos(page)
    boton(page, "CHECK-OUT").click()
    ultimo_aviso(page)
    page.wait_for_url("**/promotor/jornada")
    time.sleep(1)
    limpiar_avisos(page)
    boton(page, "FINALIZAR JORNADA").click()
    page.wait_for_selector("textarea")
    time.sleep(0.6)
    captura(page, "UI-12", "finalizar_con_pendientes", "Finalizar con 2 tiendas sin visitar: el servidor exige motivo (CP-23)")
    page.fill("textarea", "Office Depot y Bodega Aurrera cerradas por inventario")
    limpiar_avisos(page)
    boton(page, "CERRAR CON MOTIVO").click()
    ultimo_aviso(page)
    time.sleep(1)
    captura(page, "UI-13", "jornada_finalizada", "Jornada finalizada con motivo: seguimiento detenido (CP-23, CP-24)")

    page.click("a[href='/promotor/historial']")
    page.wait_for_selector(".resumen-dia")
    time.sleep(2)
    captura(page, "UI-14", "historial", "Historial propio del día: tiendas, horarios, pausas y fotos", completa=True)
    ctx.close()

    # ---------------- Supervisor (panel) ----------------
    ctx = nav.new_context(viewport={"width": 1366, "height": 1300}, locale="es-MX")
    page = ctx.new_page()
    login(page, "supervisor@demo.mx")
    page.wait_for_selector("text=RESUMEN")
    time.sleep(2.5)
    captura(page, "UI-15", "supervisor_mapa", "Supervisor: estados separados, última ubicación y alertas críticas internas", completa=True)
    page.locator("tr", has_text="Marco Antonio").locator("a", has_text="Ver ruta").click()
    page.wait_for_selector(".galeria")
    time.sleep(2.5)
    captura(page, "UI-16", "supervisor_seguimiento", "Rutas del día: recorrido, visitas, incidencias y evidencias con su validación", completa=True)
    page.click("a[href='/panel/incidencias']")
    page.wait_for_selector(".tabla tbody tr")
    time.sleep(1.5)
    captura(page, "UI-17", "incidencias", "Historial de incidencias con seguimiento manual", completa=True)
    page.click("a[href='/panel/reportes']")
    page.wait_for_selector("text=GENERAR REPORTE")
    page.locator("select").nth(1).select_option("Diario")
    page.locator("select").nth(2).select_option("Exhibición")
    boton(page, "GENERAR REPORTE").click()
    page.wait_for_selector("text=Vista previa")
    time.sleep(1)
    captura(page, "UI-18", "reporte", "Reporte diario de exhibición generado con datos reales (CP-26)", completa=True)
    href = page.locator("a", has_text="PDF").first.get_attribute("href")
    pdf = page.request.get(f"{BASE}{href}")
    open(f"{SALIDA}/UI-19_reporte.pdf", "wb").write(pdf.body())
    registro.append({"id": "UI-19", "archivo": "UI-19_reporte.pdf", "descripcion": "PDF descargado", "bytes": len(pdf.body()),
                     "tipo": pdf.headers.get("content-type")})
    page.click("a[href='/panel/asignacion']")
    page.wait_for_selector("app-selector-promotor select")
    time.sleep(1)
    page.locator("app-selector-promotor select").select_option(label="Julieta Vengas (SR-093)")
    time.sleep(1)
    for t in ("walmart", "office"):
        page.fill(".buscador input", t)
        page.wait_for_selector(".sugerencias button")
        page.locator(".sugerencias button").first.click()
    limpiar_avisos(page)
    boton(page, "GUARDAR RUTA").click()
    ultimo_aviso(page)
    time.sleep(1.5)
    captura(page, "UI-20", "asignacion", "Gestión de rutas: asignación manual por fecha y orden (advertencia por cantidad)", completa=True)
    ctx.close()

    # ---------------- Administrador (panel) ----------------
    ctx = nav.new_context(viewport={"width": 1366, "height": 1300}, locale="es-MX")
    page = ctx.new_page()
    login(page, "admin@demo.mx")
    page.wait_for_selector("text=BIENVENIDO")
    time.sleep(1.5)
    captura(page, "UI-21", "admin_inicio", "Administrador: resumen general, alertas y últimas actividades", completa=True)
    page.click("a[href='/panel/usuarios']")
    page.wait_for_selector(".tabla tbody tr")
    boton(page, "AGREGAR USUARIO").click()
    page.wait_for_selector(".formulario")
    limpiar_avisos(page)
    page.locator(".formulario button", has_text="GUARDAR").click()
    page.wait_for_selector(".error-campo")
    time.sleep(0.5)
    captura(page, "UI-22", "alta_campos_obligatorios", "Alta de usuario vacía: mensajes por campo obligatorio (CP-11)", completa=True)
    campos = page.locator(".formulario input")
    campos.nth(0).fill("Esmeralda Ramos Infante")
    campos.nth(1).fill("SR-095")
    campos.nth(2).fill("4775551234")
    campos.nth(3).fill("promotor@demo.mx")
    page.locator(".formulario select").nth(1).select_option(label="Juan Antonio Martínez")
    limpiar_avisos(page)
    page.locator(".formulario button", has_text="GUARDAR").click()
    page.wait_for_selector(".error-campo")
    time.sleep(0.5)
    captura(page, "UI-23", "alta_correo_duplicado", "Correo ya registrado: el servidor rechaza el duplicado (CP-12)", completa=True)
    campos.nth(3).fill("esmeralda@demo.mx")
    limpiar_avisos(page)
    page.locator(".formulario button", has_text="GUARDAR").click()
    page.wait_for_selector(".destacado")
    time.sleep(0.5)
    # La contraseña temporal no debe quedar en la evidencia: se tapa antes de capturar.
    page.evaluate("""() => document.querySelectorAll('.destacado .clave b').forEach(e => {
        e.textContent = '•••••••• (oculta en la evidencia)'; })""")
    captura(page, "UI-24", "alta_usuario", "Usuario creado: la contraseña temporal se muestra una sola vez (aquí oculta a propósito)", completa=True)
    page.click("a[href='/panel/tiendas']")
    page.wait_for_selector(".tabla tbody tr")
    boton(page, "AGREGAR TIENDAS").click()
    page.wait_for_selector(".formulario")
    page.locator(".formulario input").nth(0).fill("Office Max")
    limpiar_avisos(page)
    page.locator(".formulario button", has_text="GUARDAR").click()
    page.wait_for_selector(".error-campo")
    time.sleep(1)
    captura(page, "UI-25", "tienda_sin_coordenadas", "Alta de tienda sin coordenadas: rechazo esperado (CP-27)", completa=True)
    page.click("a[href='/panel/parametros']")
    page.wait_for_selector(".tabla tbody tr")
    time.sleep(1)
    captura(page, "UI-26", "parametros", "Parámetros globales (tolerancias 20 y 30 min separadas)", completa=True)
    ctx.close()

    # ---------------- Permisos desde Angular ----------------
    ctx = nav.new_context(viewport={"width": 430, "height": 900}, device_scale_factor=2, locale="es-MX")
    page = ctx.new_page()
    login(page, "promotor@demo.mx")
    page.wait_for_selector(".mosaico")
    r = page.evaluate("Promise.all(['/api/usuarios','/api/supervision/mapa','/api/reportes'].map(u => fetch(u).then(x => u + ' → ' + x.status)))")
    page.goto(f"{BASE}/panel/usuarios")
    page.wait_for_selector(".mosaico")
    page.evaluate("""(lineas) => { const d = document.createElement('pre'); d.style.cssText='background:#fff;color:#111;padding:8px;font-size:12px';
        d.textContent = 'Promotor escribe /panel/usuarios → redirigido a ' + location.pathname + '\\nPeticiones manipuladas a la API:\\n' + lineas.join('\\n');
        document.querySelector('.movil__contenido').prepend(d); }""", r)
    captura(page, "UI-27", "permisos_promotor", "Promotor sin acceso al panel: la ruta redirige y la API responde 403 (CP-10, CP-13)")
    ctx.close()
    nav.close()

json.dump(registro, open(f"{SALIDA}/capturas_interfaz.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(registro)} capturas")
