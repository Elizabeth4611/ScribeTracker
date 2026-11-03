"""Parámetros globales (tabla Parametro).

Si un parámetro no existe en la base se usa su valor por defecto, así el
sistema funciona aunque la tabla esté vacía.
"""
from app.extensions import db
from app.models import Parametro
from app.servicios.tiempo import ahora

# clave: (descripción, tipo, default, rango, categoría)
DEFINICIONES = {
    "radio_geocerca_default_m": ("Radio de geocerca sugerido para tiendas nuevas (m)", "int", "50", "10-1000", "Geolocalización"),
    "gps_intervalo_min": ("Frecuencia de envío de ubicación durante la jornada (min). RNF-15: 5 a 10", "int", "10", "1-10", "Geolocalización"),
    "ubicacion_reciente_min": ("Antigüedad máxima para considerar reciente la última ubicación (min)", "int", "20", "2-120", "Geolocalización"),
    "hora_entrada": ("Hora de entrada de la jornada (HH:MM)", "hora", "08:00", None, "Jornada"),
    "hora_salida": ("Hora de salida de la jornada (HH:MM)", "hora", "17:00", None, "Jornada"),
    "tolerancia_retardo_min": ("Tolerancia para registrar retardo al iniciar jornada (min). Entrevista P16: 20", "int", "20", "0-120", "Jornada"),
    "alerta_sin_llegada_min": ("Minutos tras la hora de entrada para alerta crítica si no hay check-in en la primera tienda. RF-11: 30", "int", "30", "5-240", "Alertas"),
    "inactividad_min": ("Minutos sin movimiento fuera de tienda para alerta de inactividad. RF-11: 120", "int", "120", "30-480", "Alertas"),
    "inactividad_radio_m": ("Radio en metros dentro del cual se considera que no hubo movimiento", "int", "100", "20-1000", "Alertas"),
    "pausa_comida_min": ("Duración de la pausa de comida (min). RF-08: 60", "int", "60", "15-120", "Pausas"),
    "pausa_descanso_min": ("Duración de cada pausa de descanso (min). RF-08: 20", "int", "20", "5-60", "Pausas"),
    "pausas_comida_max": ("Pausas de comida permitidas por jornada. RF-08: 1", "int", "1", "0-3", "Pausas"),
    "pausas_descanso_max": ("Pausas de descanso permitidas por jornada. RF-08: 2", "int", "2", "0-5", "Pausas"),
    "tiendas_sugeridas_min": ("Mínimo sugerido de tiendas por día (solo advertencia). RF-09: 3", "int", "3", "1-10", "Rutas"),
    "tiendas_sugeridas_max": ("Máximo sugerido de tiendas por día (solo advertencia). RF-09: 4", "int", "4", "1-15", "Rutas"),
}


def valor(clave: str):
    p = db.session.execute(db.select(Parametro).where(Parametro.clave == clave)).scalar_one_or_none()
    tipo = DEFINICIONES[clave][1]
    crudo = p.valor_activo if p else DEFINICIONES[clave][2]
    return int(crudo) if tipo == "int" else crudo


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
    return n
