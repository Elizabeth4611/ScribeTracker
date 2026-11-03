"""Alertas automáticas (RF-11). Canal: notificación interna en el panel.

Se evalúan cuando el supervisor o el administrador consultan el panel; no
hay un proceso en segundo plano. Las alertas críticas son:
- No llegó a su primera tienda (sin jornada ni check-in a la hora de entrada
  más el parámetro alerta_sin_llegada_min).
- Inactividad: jornada abierta, sin pausa, SIN visita abierta y sin moverse
  durante inactividad_min. Dentro de una tienda no se alerta, porque hay
  tiendas con permanencias de varias horas (entrevista, P10-P11).
- Fotos sospechosas (fuera de geocerca o repetidas): se registran al subirlas.
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Jornada, Ubicacion, Usuario, Visita
from app.servicios import operacion as op
from app.servicios import parametros
from app.servicios.geo import distancia_m
from app.servicios.tiempo import ahora


def evaluar(fecha, ids_promotores: list[int]) -> int:
    if not ids_promotores:
        return 0
    n = 0
    t = ahora()
    if fecha != t.date():
        return 0
    h, m = (int(x) for x in parametros.valor("hora_entrada").split(":"))
    limite_llegada = datetime(fecha.year, fecha.month, fecha.day, h, m) + timedelta(
        minutes=parametros.valor("alerta_sin_llegada_min"))
    ventana = timedelta(minutes=parametros.valor("inactividad_min"))
    radio = parametros.valor("inactividad_radio_m")

    for p in db.session.execute(db.select(Usuario).where(
            Usuario.id_usuario.in_(ids_promotores), Usuario.estatus == "Activo")).scalars():
        asignaciones = op.asignaciones_del_dia(p.id_usuario, fecha)
        if not asignaciones:
            continue
        j = op.jornada_de(p.id_usuario, fecha)
        if t > limite_llegada and j is None:
            primera = asignaciones[0].tienda
            if op.registrar_incidencia(
                    p.id_usuario, "Sin llegada a primera tienda",
                    f"A las {limite_llegada:%H:%M} no había iniciado jornada en {primera.nombre_comercial} {primera.sucursal}.",
                    critica=True, clave=f"sinllegada:{p.id_usuario}:{fecha.isoformat()}"):
                n += 1
        if j is None or j.estado != "Abierta" or op.pausa_activa(j) or op.visita_abierta(p.id_usuario):
            continue
        # Desde cuándo está fuera de tienda y sin pausa
        ultimo_hito = max([j.fecha_hora_inicio] + [v.fecha_hora_checkout for v in j.visitas if v.fecha_hora_checkout]
                          + [pa.fecha_hora_fin for pa in j.pausas if pa.fecha_hora_fin])
        if t - ultimo_hito < ventana:
            continue
        puntos = db.session.execute(db.select(Ubicacion).where(
            Ubicacion.id_jornada == j.id_jornada, Ubicacion.fecha_hora_captura >= t - ventana)
            .order_by(Ubicacion.fecha_hora_captura)).scalars().all()
        bloque = int((t - j.fecha_hora_inicio) / ventana)
        if not puntos:
            if op.registrar_incidencia(
                    p.id_usuario, "Sin ubicación reciente",
                    f"Sin ubicaciones recibidas en los últimos {int(ventana.total_seconds() // 60)} min "
                    "(GPS apagado, sin señal o navegador cerrado).",
                    critica=True, clave=f"sinsenal:{j.id_jornada}:{bloque}", id_jornada=j.id_jornada):
                n += 1
            continue
        ref = puntos[-1]
        if all(distancia_m(ref.latitud, ref.longitud, u.latitud, u.longitud) <= radio for u in puntos):
            if op.registrar_incidencia(
                    p.id_usuario, "Inactividad",
                    f"Sin moverse más de {radio} m durante {int(ventana.total_seconds() // 60)} min fuera de tienda.",
                    critica=True, clave=f"inactividad:{j.id_jornada}:{bloque}", id_jornada=j.id_jornada):
                n += 1
    db.session.commit()
    return n
