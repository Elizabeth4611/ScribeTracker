"""Caso CP-28 (F08): estado de la pantalla justo después de sincronizar.

Reproduce, con la aplicación tal como está compilada, el flujo: jornada,
visita completa en Walmart, pérdida de señal, check-in en Soriana sin
conexión y recuperación de la señal. A los 5 s de recuperar la señal guarda
una captura y compara lo que muestra la pantalla con lo que tiene el
servidor. Uso: python reproducir_sincronizacion.py <url> <salida> <sufijo> <entorno>
"""
import json
import os
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

BASE, SALIDA, SUFIJO, ENTORNO = sys.argv[1:5]
M = 1 / 111_320
WALMART = (21.1458, -101.6893)
SORIANA = (21.1395, -101.7104)

with sync_playwright() as pw:
    nav = pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    ctx = nav.new_context(viewport={"width": 430, "height": 900}, device_scale_factor=2, locale="es-MX",
                          geolocation={"latitude": WALMART[0] + 10 * M, "longitude": WALMART[1], "accuracy": 12},
                          permissions=["geolocation", "camera"])
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.fill("input[type=email]", "promotor@demo.mx")
    page.fill("input[type=password]", os.environ["ST_DEMO_PASSWORD"])
    page.click("button[type=submit]")
    page.wait_for_selector(".mosaico")
    # Preparación por API (mismas reglas del servidor) para llegar al punto del caso.
    prep = page.evaluate("""async ([lat, lon]) => {
        const j = (u, b) => fetch(u, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(b)}).then(r => r.json());
        await j('/api/promotor/jornada/iniciar', {latitud: lat, longitud: lon, precision: 10});
        const hoy = await fetch('/api/promotor/hoy').then(r => r.json());
        const v = (await j('/api/promotor/visitas/checkin', {id_asignacion: hoy.asignaciones[0].id_asignacion, latitud: lat, longitud: lon, precision: 10})).visita;
        for (const c of ['Anaquel antes', 'Anaquel después', 'Precios', 'Promociones']) {
            const f = new FormData();
            Object.entries({categoria: c, id_visita: v.id_visita, latitud: lat, longitud: lon, precision: 10}).forEach(([k, x]) => f.append(k, x));
            const cv = document.createElement('canvas'); cv.width = 320; cv.height = 240;
            const g = cv.getContext('2d'); g.fillStyle = '#' + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, '0');
            g.fillRect(0, 0, 320, 240); g.fillStyle = '#000'; g.font = '20px sans-serif'; g.fillText(c, 20, 120);
            const blob = await new Promise(r => cv.toBlob(r, 'image/jpeg', 0.9));
            f.append('foto', blob, 'f.jpg');
            const r = await fetch('/api/promotor/evidencias', {method: 'POST', body: f});
            if (!r.ok) throw new Error('evidencia ' + r.status + ' ' + await r.text());
        }
        const co = await j('/api/promotor/visitas/checkout', {id_visita: v.id_visita, latitud: lat, longitud: lon, precision: 10});
        return co.mensaje || JSON.stringify(co);
    }""", [WALMART[0] + 10 * M, WALMART[1]])
    print("Preparación:", prep)
    page.reload()  # la preparación se hizo por API: la app debe leer el estado nuevo
    page.wait_for_selector(".mosaico")
    page.click("a[href='/promotor/jornada']")
    page.wait_for_selector(".lista-tiendas")
    time.sleep(1.5)
    print("Lista inicial:", page.eval_on_selector_all(".lista-tiendas li", "els => els.map(e => e.innerText.replace(/\\n/g, ' | '))"))

    # Paso del caso: sin señal, check-in en Soriana
    ctx.set_geolocation({"latitude": SORIANA[0] + 10 * M, "longitude": SORIANA[1], "accuracy": 12})
    ctx.set_offline(True)
    page.locator("button", has_text="CHECK-IN").first.click()
    page.wait_for_selector(".franja")
    time.sleep(1)
    # Recupera la señal
    ctx.set_offline(False)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    time.sleep(5)

    pantalla = {
        "franja": page.eval_on_selector(".franja", "e => e.innerText") if page.query_selector(".franja") else "(sin franja)",
        "soriana": page.eval_on_selector_all(".lista-tiendas li", "els => els[1].innerText.replace(/\\n/g, ' | ')"),
        "visita_en_curso": page.eval_on_selector(".tarjeta-oscura", "e => e.innerText.replace(/\\n/g, ' | ')") if page.query_selector(".tarjeta-oscura") else "(ninguna)",
        "boton_checkin_soriana": page.locator(".lista-tiendas li").nth(1).locator("button", has_text="CHECK-IN").count() > 0,
    }
    servidor = page.evaluate("fetch('/api/promotor/hoy').then(r => r.json()).then(d => d.asignaciones[1].visita && "
                             "({estado: d.asignaciones[1].visita.estado, origen: d.asignaciones[1].visita.origen, checkin: d.asignaciones[1].visita.checkin}))")
    texto = (f"CP-28 · {SUFIJO} · 5 s después de recuperar la señal\n"
             f"Pantalla: {pantalla['soriana']} · botón CHECK-IN visible: {pantalla['boton_checkin_soriana']}\n"
             f"Servidor: visita Soriana {servidor}\n{ENTORNO} · {datetime.now():%d/%m/%Y %H:%M:%S}")
    page.evaluate("""(t) => { const d = document.createElement('div');
        d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#111827;color:#fde68a;font:12px/1.35 Consolas,monospace;padding:6px 10px;border-top:2px solid #f59e0b;white-space:pre-wrap';
        d.textContent = t; document.body.appendChild(d); }""", texto)
    time.sleep(0.4)
    page.screenshot(path=f"{SALIDA}/CP-28_{SUFIJO}.png")
    json.dump({"pantalla": pantalla, "servidor": servidor, "hora": datetime.now().isoformat(timespec="seconds")},
              open(f"{SALIDA}/CP-28_{SUFIJO}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"pantalla": pantalla, "servidor": servidor}, ensure_ascii=False, indent=1))
    nav.close()
