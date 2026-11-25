"""Parámetros globales (tabla Parametro).

Si un parámetro no existe en la base se usa su valor por defecto, así el
sistema funciona aunque la tabla esté vacía.
"""
from app.extensions import db
from app.models import Parametro
from app.servicios.tiempo import ahora

# clave: (nombre, tipo, default, rango, categoría)
DEFINICIONES = {
    "hora_entrada": ("Hora de entrada", "hora", "08:00", None, "Jornada"),
    "hora_salida": ("Hora de salida", "hora", "17:00", None, "Jornada"),
    "tolerancia_retardo_min": ("Tolerancia de retardo", "int", "20", "0-120", "Jornada"),
    "pausa_comida_min": ("Duración de la comida", "int", "60", "15-120", "Pausas"),
    "pausas_comida_max": ("Comidas permitidas por jornada", "int", "1", "0-3", "Pausas"),
    "pausa_descanso_min": ("Duración de cada descanso", "int", "20", "5-60", "Pausas"),
    "pausas_descanso_max": ("Descansos permitidos por jornada", "int", "2", "0-5", "Pausas"),
    "alerta_sin_llegada_min": ("Alerta si no llega a su primera tienda", "int", "30", "5-240", "Alertas"),
    "inactividad_min": ("Alerta por inactividad", "int", "120", "30-480", "Alertas"),
    "inactividad_radio_m": ("Distancia para considerar que no se movió", "int", "100", "20-1000", "Alertas"),
    "gps_intervalo_min": ("Cada cuánto se envía la ubicación", "int", "10", "1-10", "Ubicación y geocerca"),
    "ubicacion_reciente_min": ("Ubicación reciente", "int", "20", "2-120", "Ubicación y geocerca"),
    "radio_geocerca_default_m": ("Radio de la geocerca para tiendas nuevas", "int", "50", "10-1000", "Ubicación y geocerca"),
    "tiendas_sugeridas_min": ("Mínimo de tiendas por día", "int", "3", "1-10", "Rutas"),
    "tiendas_sugeridas_max": ("Máximo de tiendas por día", "int", "4", "1-15", "Rutas"),
    "login_intentos_max": ("Intentos antes de bloquear la cuenta", "int", "3", "1-10", "Seguridad"),
    "login_bloqueo_min": ("Tiempo de bloqueo de la cuenta", "int", "15", "1-1440", "Seguridad"),
}

# Explicación sencilla y unidad que se muestran en la pantalla de Parámetros.
AYUDA = {
    "hora_entrada": ("Hora a la que empieza la jornada de los promotores. Se usa para marcar retardos y la alerta de llegada.", "hora"),
    "hora_salida": ("Hora a la que termina la jornada. En los reportes, cerrar antes de esta hora cuenta como salida anticipada.", "hora"),
    "tolerancia_retardo_min": ("Minutos después de la hora de entrada en los que el promotor todavía puede iniciar su jornada sin que cuente como retardo.", "minutos"),
    "pausa_comida_min": ("Cuánto dura la pausa de comida.", "minutos"),
    "pausas_comida_max": ("Cuántas veces puede tomar comida el promotor en un día.", "veces"),
    "pausa_descanso_min": ("Cuánto dura cada pausa de descanso.", "minutos"),
    "pausas_descanso_max": ("Cuántos descansos puede tomar el promotor en un día.", "veces"),
    "alerta_sin_llegada_min": ("Si pasado este tiempo desde la hora de entrada el promotor no ha hecho check-in en su primera tienda, el supervisor recibe una alerta crítica.", "minutos"),
    "inactividad_min": ("Si el promotor pasa este tiempo sin moverse fuera de una tienda, el supervisor recibe una alerta.", "minutos"),
    "inactividad_radio_m": ("Mientras el promotor se mueva menos de esta distancia, el sistema considera que no se ha movido.", "metros"),
    "gps_intervalo_min": ("Durante la jornada, el celular del promotor manda su ubicación cada este número de minutos.", "minutos"),
    "ubicacion_reciente_min": ("Si la última ubicación del promotor es más antigua que esto, el mapa la muestra como desactualizada.", "minutos"),
    "radio_geocerca_default_m": ("Qué tan cerca de la tienda debe estar el promotor para hacer check-in y tomar fotos. Es el valor que se propone al dar de alta una tienda; cada tienda puede tener el suyo.", "metros"),
    "tiendas_sugeridas_min": ("Al armar una ruta, el sistema avisa si el promotor tiene menos tiendas que esto. Solo es un aviso: sí deja guardar.", "tiendas"),
    "tiendas_sugeridas_max": ("Al armar una ruta, el sistema avisa si el promotor tiene más tiendas que esto. Solo es un aviso: sí deja guardar.", "tiendas"),
    "login_intentos_max": ("Contraseñas incorrectas seguidas que se permiten antes de bloquear la cuenta.", "intentos"),
    "login_bloqueo_min": ("Cuánto tiempo queda bloqueada la cuenta después de esos intentos.", "minutos"),
}

ORDEN_CATEGORIAS = ["Jornada", "Pausas", "Alertas", "Ubicación y geocerca", "Rutas", "Seguridad"]


def valor(clave: str):
    # Corrección F13 (desempeño): se leían los parámetros con una consulta cada
    # vez (cientos por petición en el mapa). Ahora se leen todos una sola vez
    # por petición y se guardan en flask.g.
    from flask import g, has_app_context
    cache = None
    if has_app_context():
        cache = g.get("_st_param")
        if cache is None:
            cache = {x.clave: x.valor_activo for x in db.session.execute(db.select(Parametro)).scalars()}
            g._st_param = cache
        crudo = cache.get(clave, DEFINICIONES[clave][2])
    else:
        p = db.session.execute(db.select(Parametro).where(Parametro.clave == clave)).scalar_one_or_none()
        crudo = p.valor_activo if p else DEFINICIONES[clave][2]
    tipo = DEFINICIONES[clave][1]
    return int(crudo) if tipo == "int" else crudo


def olvidar_cache() -> None:
    from flask import g, has_app_context
    if has_app_context():
        g.pop("_st_param", None)


def validar(clave: str, crudo: str) -> str:
    """Devuelve el valor normalizado o lanza ValueError con un mensaje claro."""
    _, tipo, _, rango, _ = DEFINICIONES[clave]
    crudo = str(crudo).strip()
    if tipo == "int":
        try:
            n = int(crudo)
        except ValueError:
            raise ValueError("Debe ser un número entero.")
        if rango:
            lo, hi = (int(x) for x in rango.split("-"))
            if not lo <= n <= hi:
                raise ValueError(f"Debe estar entre {lo} y {hi}.")
        return str(n)
    if tipo == "hora":
        partes = crudo.split(":")
        if len(partes) != 2 or not all(x.isdigit() for x in partes):
            raise ValueError("Usa el formato HH:MM.")
        h, m = int(partes[0]), int(partes[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Hora no válida.")
        return f"{h:02d}:{m:02d}"
    return crudo


def sembrar() -> int:
    """Crea los parámetros que falten con su valor por defecto."""
    existentes = set(db.session.execute(db.select(Parametro.clave)).scalars())
    n = 0
    for clave, (desc, tipo, default, rango, cat) in DEFINICIONES.items():
        if clave not in existentes:
            db.session.add(Parametro(
                clave=clave, descripcion=desc, tipo_dato=tipo, valor_activo=default,
                valor_default=default, rango=rango, categoria=cat, fecha_modificacion=ahora(),
            ))
            n += 1
    db.session.commit()
    olvidar_cache()
    return n
