"""Cálculo de distancias para las geocercas.

La geocerca valida las coordenadas que envía el dispositivo; por sí sola no
garantiza que esas coordenadas sean auténticas (una app de GPS simulado
puede falsearlas y un navegador web no puede detectarlo).
"""
import math

RADIO_TIERRA_M = 6_371_000


def distancia_m(lat1, lon1, lat2, lon2) -> float:
    """Distancia en metros (fórmula de Haversine)."""
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2 - p1
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def dentro_de_tienda(tienda, lat, lon) -> tuple[bool, float]:
    d = distancia_m(tienda.latitud, tienda.longitud, lat, lon)
    return d <= tienda.radio_geocerca_m, round(d, 1)
