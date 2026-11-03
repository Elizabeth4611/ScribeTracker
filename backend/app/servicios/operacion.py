"""Reglas de jornada, visitas, pausas, estados e incidencias.

Todas las reglas se aplican aquí, en el servidor; la interfaz solo las
refleja. Las funciones reciben la hora de captura del dispositivo porque
en el modo sin conexión el evento llega después de ocurrir.
"""
from datetime import datetime, timedelta

from flask import request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Asignacion, Evidencia, Incidencia, Jornada, Pausa, Tienda, Ubicacion, Visita
from app.models.operacion import CATEGORIAS
from app.servicios import parametros
from app.servicios.geo import distancia_m
from app.servicios.tiempo import ahora

PRECISION_MAXIMA_M = 500       # lecturas peores se rechazan por imprecisas
DESFASE_FUTURO_MAX = timedelta(minutes=2)
VELOCIDAD_SOSPECHOSA_KMH = 200


class ReglaError(Exception):
    """Violación de una regla de negocio: se responde con 409 o 400."""

    def __init__(self, mensaje: str, codigo: int = 409, **extra):
        super().__init__(mensaje)
        self.mensaje, self.codigo, self.extra = mensaje, codigo, extra


# ------------------------------------------------------------- entradas

def leer_ubicacion(datos) -> tuple[float, float, float | None]:
    try:
        lat = float(datos.get("latitud"))
        lon = float(datos.get("longitud"))
    except (TypeError, ValueError):
        raise ReglaError("No se recibió tu ubicación. Activa el GPS y permite el acceso a la ubicación.", 400)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ReglaError("La ubicación recibida no es válida.", 400)
    prec = datos.get("precision")
    try:
        prec = round(float(prec), 1) if prec not in (None, "") else None
    except (TypeError, ValueError):
        prec = None
    if prec is not None and prec > PRECISION_MAXIMA_M:
        raise ReglaError(f"La señal GPS es muy imprecisa (±{int(prec)} m). Sal a un área abierta e intenta de nuevo.", 400)
    return lat, lon, prec


def leer_captura(datos) -> datetime:
    """Hora en que ocurrió el evento en el dispositivo (modo sin conexión).
    Sin dato, se usa la hora del servidor. No se aceptan horas futuras."""
    crudo = datos.get("capturado_en")
    servidor = ahora()
    if not crudo:
        return servidor
    try:
        t = datetime.fromisoformat(str(crudo).replace("Z", ""))
    except ValueError:
        raise ReglaError("La fecha de captura no es válida.", 400)
    t = t.replace(tzinfo=None, microsecond=0)
    if t - servidor > DESFASE_FUTURO_MAX:
        raise ReglaError("La hora del dispositivo está adelantada. Corrige la fecha y hora del teléfono.", 400)
    return t


def origen_peticion() -> str:
    return "Sin conexión" if request.headers.get("X-Origen") == "sin-conexion" else "En línea"


# ------------------------------------------------------------ consultas

def asignaciones_del_dia(id_promotor: int, fecha) -> list[Asignacion]:
    return db.session.execute(db.select(Asignacion).join(Tienda).where(
        Asignacion.id_promotor == id_promotor, Asignacion.fecha == fecha,
        Asignacion.estado == "Activa").order_by(Asignacion.orden_visita)).scalars().all()


def jornada_de(id_promotor: int, fecha) -> Jornada | None:
    return db.session.execute(db.select(Jornada).where(
        Jornada.id_promotor == id_promotor, Jornada.fecha == fecha)).scalar_one_or_none()


def jornada_abierta(id_promotor: int) -> Jornada | None:
    return db.session.execute(db.select(Jornada).where(
        Jornada.id_promotor == id_promotor, Jornada.estado == "Abierta")
        .order_by(Jornada.fecha.desc())).scalars().first()


def pausa_activa(jornada: Jornada | None) -> Pausa | None:
    if jornada is None:
        return None
    return db.session.execute(db.select(Pausa).where(
        Pausa.id_jornada == jornada.id_jornada, Pausa.fecha_hora_fin.is_(None))).scalar_one_or_none()


def visita_abierta(id_promotor: int) -> Visita | None:
    return db.session.execute(db.select(Visita).where(
        Visita.id_promotor == id_promotor, Visita.estado == "Abierta")).scalar_one_or_none()


def categorias_validas(visita: Visita) -> set[str]:
    return {e.categoria for e in visita.evidencias if e.estatus_validacion == "Válida"}


def categorias_faltantes(visita: Visita) -> list[str]:
    tiene = categorias_validas(visita)
    return [c for c in CATEGORIAS if c not in tiene]


def registrar_incidencia(id_promotor, tipo, descripcion, critica=False, clave=None, **refs) -> Incidencia | None:
    """Crea una incidencia; si `clave` ya existe no se duplica."""
    if clave and db.session.execute(db.select(Incidencia.id_incidencia).where(
            Incidencia.clave_unica == clave)).first():
        return None
    inc = Incidencia(id_promotor=id_promotor, tipo=tipo, es_critica=critica, fecha_hora=ahora(),
                     descripcion=descripcion, estado="Pendiente", clave_unica=clave, origen="Sistema", **refs)
    db.session.add(inc)
    db.session.flush()
    return inc


def _hora_param(fecha, clave) -> datetime:
    h, m = (int(x) for x in parametros.valor(clave).split(":"))
    return datetime(fecha.year, fecha.month, fecha.day, h, m)


# --------------------------------------------------------------- jornada

def iniciar_jornada(promotor, lat, lon, prec, captura) -> Jornada:
    fecha = captura.date()
    if jornada_de(promotor.id_usuario, fecha) is not None:
        raise ReglaError("Ya registraste una jornada para este día. Solo se permite una jornada por fecha.")
    otra = jornada_abierta(promotor.id_usuario)
    if otra is not None:
        raise ReglaError(f"Tienes una jornada abierta del {otra.fecha.isoformat()}. Finalízala antes de iniciar otra.")
    asignaciones = asignaciones_del_dia(promotor.id_usuario, fecha)
    if not asignaciones:
        raise ReglaError("No tienes tiendas asignadas para hoy. Consulta a tu supervisor.")
    primera = asignaciones[0]
    t = primera.tienda
    d = round(distancia_m(t.latitud, t.longitud, lat, lon), 1)
    if d > t.radio_geocerca_m:
        raise ReglaError(
            f"Para iniciar tu jornada debes estar en tu primera tienda: {t.nombre_comercial} {t.sucursal}. "
            f"Estás a {int(d)} m y el radio permitido es de {t.radio_geocerca_m} m.",
            distancia_m=d, radio_m=t.radio_geocerca_m, id_tienda=t.id_tienda)
    j = Jornada(id_promotor=promotor.id_usuario, fecha=fecha, fecha_hora_inicio=captura,
                latitud_inicio=lat, longitud_inicio=lon, precision_inicio_m=prec,
                id_tienda_inicio=t.id_tienda, distancia_inicio_m=d, estado="Abierta",
                fecha_hora_recepcion=ahora(), origen=origen_peticion())
    db.session.add(j)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ReglaError("Ya registraste una jornada para este día.")
    limite = _hora_param(fecha, "hora_entrada") + timedelta(minutes=parametros.valor("tolerancia_retardo_min"))
    if captura > limite:
        minutos = int((captura - limite).total_seconds() // 60) + parametros.valor("tolerancia_retardo_min")
        registrar_incidencia(promotor.id_usuario, "Retardo",
                             f"Inició jornada a las {captura:%H:%M} ({minutos} min después de la hora de entrada).",
                             clave=f"retardo:{j.id_jornada}", id_jornada=j.id_jornada)
    # La ubicación de inicio también es el primer punto del seguimiento.
    db.session.add(Ubicacion(id_promotor=promotor.id_usuario, id_jornada=j.id_jornada, latitud=lat,
                             longitud=lon, precision_m=prec, fecha_hora_captura=captura,
                             fecha_hora_recepcion=ahora(), origen=origen_peticion()))
    db.session.commit()
    return j


def finalizar_jornada(promotor, lat, lon, prec, captura, forzar=False, motivo="") -> Jornada:
    j = jornada_abierta(promotor.id_usuario)
    if j is None:
        raise ReglaError("No tienes una jornada abierta.")
    if visita_abierta(promotor.id_usuario) is not None:
        raise ReglaError("Tienes una visita abierta. Registra el check-out antes de finalizar la jornada.")
    if pausa_activa(j) is not None:
        raise ReglaError("Tienes una pausa activa. Termínala antes de finalizar la jornada.")
    cerradas = {v.id_asignacion for v in j.visitas if v.estado == "Cerrada"}
    pendientes = [a for a in asignaciones_del_dia(promotor.id_usuario, j.fecha) if a.id_asignacion not in cerradas]
    nombres = [f"{a.tienda.nombre_comercial} {a.tienda.sucursal}" for a in pendientes]
    if pendientes and not forzar:
        raise ReglaError("Aún tienes tiendas asignadas sin visitar. Complétalas o indica el motivo para cerrar.",
                         pendientes=nombres, puede_forzar=True)
    motivo = " ".join(str(motivo or "").split())
    if pendientes and len(motivo) < 10:
        raise ReglaError("Escribe el motivo (al menos 10 caracteres) para cerrar con tiendas pendientes.", 400,
                         pendientes=nombres, puede_forzar=True)
    if captura < j.fecha_hora_inicio:
        raise ReglaError("La hora de cierre es anterior al inicio de la jornada.", 400)
    j.fecha_hora_fin, j.latitud_fin, j.longitud_fin = captura, lat, lon
    j.estado = "Finalizada"
    if pendientes:
        j.cierre_forzado, j.motivo_cierre = True, motivo[:300]
        registrar_incidencia(promotor.id_usuario, "Jornada cerrada con tiendas pendientes",
                             f"Pendientes: {', '.join(nombres)}. Motivo: {motivo}",
                             clave=f"cierre:{j.id_jornada}", id_jornada=j.id_jornada)
    db.session.commit()
    return j


# --------------------------------------------------------------- visitas

def _exigir_jornada_sin_pausa(promotor, captura) -> Jornada:
    j = jornada_abierta(promotor.id_usuario)
    if j is None or j.fecha != captura.date():
        raise ReglaError("Primero inicia tu jornada del día.")
    if pausa_activa(j) is not None:
        raise ReglaError("Estás en pausa. Termina la pausa para continuar.")
    if captura < j.fecha_hora_inicio:
        raise ReglaError("La hora del registro es anterior al inicio de tu jornada.", 400)
    return j


def checkin(promotor, id_asignacion, lat, lon, prec, captura, id_cliente=None) -> Visita:
    j = _exigir_jornada_sin_pausa(promotor, captura)
    a = db.session.get(Asignacion, id_asignacion) if id_asignacion else None
    if a is None or a.id_promotor != promotor.id_usuario or a.estado != "Activa" or a.fecha != j.fecha:
        raise ReglaError("Esa tienda no está asignada para tu jornada de hoy.", 404)
    abierta = visita_abierta(promotor.id_usuario)
    if abierta is not None:
        raise ReglaError(f"Ya tienes una visita abierta en {abierta.tienda.nombre_comercial}. "
                         "Registra su check-out antes de entrar a otra tienda.")
    if db.session.execute(db.select(Visita.id_visita).where(Visita.id_asignacion == a.id_asignacion)).first():
        raise ReglaError("Ya registraste la visita a esta tienda hoy.")
    t = a.tienda
    d = round(distancia_m(t.latitud, t.longitud, lat, lon), 1)
    if d > t.radio_geocerca_m:
        raise ReglaError(f"No estás dentro del radio permitido de la tienda: estás a {int(d)} m y el radio es "
                         f"de {t.radio_geocerca_m} m.", distancia_m=d, radio_m=t.radio_geocerca_m)
    v = Visita(id_jornada=j.id_jornada, id_promotor=promotor.id_usuario, id_tienda=t.id_tienda,
               id_asignacion=a.id_asignacion, id_cliente=id_cliente, estado="Abierta",
               fecha_hora_checkin=captura, latitud_checkin=lat, longitud_checkin=lon, precision_checkin_m=prec,
               distancia_checkin_m=d, recepcion_checkin=ahora(), origen=origen_peticion())
    db.session.add(v)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ReglaError("Ya tienes una visita abierta o esta tienda ya fue registrada.")
    return v


def buscar_visita(promotor, id_visita=None, visita_cliente=None) -> Visita:
    v = None
    if id_visita:
        v = db.session.get(Visita, int(id_visita))
    elif visita_cliente:
        v = db.session.execute(db.select(Visita).where(Visita.id_cliente == str(visita_cliente))).scalar_one_or_none()
    if v is None or v.id_promotor != promotor.id_usuario:
        raise ReglaError("Visita no encontrada.", 404)
    return v


def checkout(promotor, visita: Visita, lat, lon, prec, captura) -> Visita:
    _exigir_jornada_sin_pausa(promotor, captura)
    if visita.estado != "Abierta":
        raise ReglaError("Esta visita ya tiene check-out.")
    if captura < visita.fecha_hora_checkin:
        raise ReglaError("La hora del check-out es anterior al check-in.", 400)
    faltan = categorias_faltantes(visita)
    if faltan:
        raise ReglaError("Faltan fotografías válidas para cerrar la visita: " + ", ".join(faltan) + ".",
                         faltantes=faltan)
    t = visita.tienda
    d = round(distancia_m(t.latitud, t.longitud, lat, lon), 1)
    if d > t.radio_geocerca_m:
        raise ReglaError(f"No estás dentro del radio permitido de la tienda: estás a {int(d)} m y el radio es "
                         f"de {t.radio_geocerca_m} m.", distancia_m=d, radio_m=t.radio_geocerca_m)
    visita.estado = "Cerrada"
    visita.fecha_hora_checkout, visita.latitud_checkout, visita.longitud_checkout = captura, lat, lon
    visita.precision_checkout_m, visita.distancia_checkout_m, visita.recepcion_checkout = prec, d, ahora()
    db.session.commit()  # la jornada sigue abierta (regla 7)
    return visita


# ---------------------------------------------------------------- pausas

def iniciar_pausa(promotor, tipo, captura) -> Pausa:
    if tipo not in ("Comida", "Descanso"):
        raise ReglaError("Selecciona Comida o Descanso.", 400)
    j = jornada_abierta(promotor.id_usuario)
    if j is None or j.fecha != captura.date():
        raise ReglaError("Primero inicia tu jornada del día.")
    if pausa_activa(j) is not None:
        raise ReglaError("Ya tienes una pausa activa.")
    usadas = sum(1 for p in j.pausas if p.tipo == tipo)
    maximo = parametros.valor("pausas_comida_max" if tipo == "Comida" else "pausas_descanso_max")
    if usadas >= maximo:
        raise ReglaError("Ya has tomado tu pausa de comida hoy." if tipo == "Comida"
                         else f"Ya usaste tus {maximo} pausas de descanso de hoy.")
    duracion = parametros.valor("pausa_comida_min" if tipo == "Comida" else "pausa_descanso_min")
    p = Pausa(id_jornada=j.id_jornada, tipo=tipo, fecha_hora_inicio=captura, duracion_programada_min=duracion)
    db.session.add(p)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ReglaError("Ya tienes una pausa activa.")
    return p


def finalizar_pausa(promotor, captura) -> Pausa:
    j = jornada_abierta(promotor.id_usuario)
    p = pausa_activa(j)
    if p is None:
        raise ReglaError("No tienes una pausa activa.")
    if captura < p.fecha_hora_inicio:
        raise ReglaError("La hora de fin es anterior al inicio de la pausa.", 400)
    p.fecha_hora_fin = captura
    real = (captura - p.fecha_hora_inicio).total_seconds() / 60
    if real > p.duracion_programada_min + 1:
        registrar_incidencia(promotor.id_usuario, "Pausa excedida",
                             f"Pausa de {p.tipo.lower()} de {int(real)} min (programada: {p.duracion_programada_min} min).",
                             clave=f"pausa:{p.id_pausa}", id_jornada=j.id_jornada)
    db.session.commit()
    return p


# ------------------------------------------------------------ ubicaciones

def registrar_ubicacion(promotor, lat, lon, prec, captura, id_cliente=None) -> Ubicacion:
    j = jornada_abierta(promotor.id_usuario)
    if j is None or j.fecha != captura.date() or captura < j.fecha_hora_inicio:
        raise ReglaError("El seguimiento solo funciona durante una jornada abierta.", codigo_rastreo="sin_jornada")
    p_activa = pausa_activa(j)
    # Una pausa cubre desde su inicio; si el punto se capturó durante una
    # pausa (aunque llegue tarde por falta de señal) no se guarda.
    en_pausa = any(p.fecha_hora_inicio <= captura and (p.fecha_hora_fin is None or captura < p.fecha_hora_fin)
                   for p in j.pausas)
    if p_activa is not None or en_pausa:
        raise ReglaError("El seguimiento está suspendido durante la pausa.", codigo_rastreo="en_pausa")
    previa = db.session.execute(db.select(Ubicacion).where(Ubicacion.id_jornada == j.id_jornada)
                                .order_by(Ubicacion.fecha_hora_captura.desc())).scalars().first()
    u = Ubicacion(id_promotor=promotor.id_usuario, id_jornada=j.id_jornada, id_cliente=id_cliente,
                  latitud=lat, longitud=lon, precision_m=prec, fecha_hora_captura=captura,
                  fecha_hora_recepcion=ahora(), origen=origen_peticion())
    db.session.add(u)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise ReglaError("Esta ubicación ya fue registrada.")
    if previa is not None and captura > previa.fecha_hora_captura:
        horas = (captura - previa.fecha_hora_captura).total_seconds() / 3600
        km = distancia_m(previa.latitud, previa.longitud, lat, lon) / 1000
        if horas > 0 and km / horas > VELOCIDAD_SOSPECHOSA_KMH and km > 1:
            registrar_incidencia(promotor.id_usuario, "Ubicación sospechosa",
                                 f"Desplazamiento de {km:.1f} km en {horas * 60:.0f} min ({km / horas:.0f} km/h).",
                                 clave=f"salto:{u.id_ubicacion}", id_jornada=j.id_jornada)
    db.session.commit()
    return u


# ----------------------------------------------------------------- estados

def estado_promotor(promotor, fecha) -> dict:
    """Estados separados: cuenta, jornada, visita y conexión."""
    j = jornada_de(promotor.id_usuario, fecha)
    pausa = pausa_activa(j) if j and j.estado == "Abierta" else None
    visita = visita_abierta(promotor.id_usuario) if j and j.estado == "Abierta" else None
    ultima = None
    if j:
        ultima = db.session.execute(db.select(Ubicacion).where(Ubicacion.id_jornada == j.id_jornada)
                                    .order_by(Ubicacion.fecha_hora_captura.desc())).scalars().first()

    if j is None:
        e_jornada = "Sin jornada"
    elif j.estado == "Finalizada":
        e_jornada = "Finalizada"
    elif pausa is not None:
        e_jornada = "En pausa"
    else:
        e_jornada = "En jornada"

    e_visita = None
    if e_jornada == "En jornada":
        e_visita = "En tienda" if visita else "En traslado"

    if e_jornada in ("En pausa", "Finalizada"):
        e_conexion = "Rastreo suspendido"
    elif ultima is None:
        e_conexion = "Sin ubicación"
    else:
        limite = parametros.valor("ubicacion_reciente_min")
        e_conexion = "Reciente" if ahora() - ultima.fecha_hora_captura <= timedelta(minutes=limite) else "Desactualizada"

    return {
        "estado_cuenta": promotor.estatus,
        "estado_jornada": e_jornada,
        "estado_visita": e_visita,
        "estado_conexion": e_conexion,
        "tienda_actual": (f"{visita.tienda.nombre_comercial} {visita.tienda.sucursal}" if visita else None),
        "ultima_ubicacion": None if ultima is None else {
            "latitud": float(ultima.latitud), "longitud": float(ultima.longitud),
            "precision_m": ultima.precision_m, "fecha_hora": ultima.fecha_hora_captura.isoformat(),
        },
        "pausa": None if pausa is None else {
            "tipo": pausa.tipo, "inicio": pausa.fecha_hora_inicio.isoformat(),
            "duracion_programada_min": pausa.duracion_programada_min,
        },
    }
