"""Hora del servidor.

Se usa la hora local del equipo donde corre Flask (la laptop está en
America/Mexico_City, UTC-6, sin horario de verano desde 2022). Las pruebas
fijan la hora con `fijar()` para simular fechas y horas.
"""
from datetime import date, datetime

_fija: datetime | None = None


def fijar(momento: datetime | None) -> None:
    global _fija
    _fija = momento


def ahora() -> datetime:
    if _fija is not None:
        return _fija
    return datetime.now().replace(microsecond=0)


def hoy() -> date:
    return ahora().date()
