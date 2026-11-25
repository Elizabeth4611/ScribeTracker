"""Reintento de conexión mientras la base de Azure SQL "despierta".

La base gratuita de Azure SQL (sin servidor) se pausa sola tras 1 hora sin uso.
La primera conexión después de la pausa falla con el error 40613 ("Database ...
is not currently available") mientras Azure la reanuda (~1 minuto). Sin esto, el
usuario veía "El servidor no puede conectarse a la base de datos". Con esto, el
servidor espera y reintenta solo; la petición únicamente tarda más.
"""
import time

from sqlalchemy import event

# Errores transitorios documentados de Azure SQL (base en pausa, reanudándose o saturada).
TRANSITORIOS = ("40613", "40197", "40501", "49918", "49919", "49920", "not currently available",
                # Mientras la base se reanuda, el inicio de sesión también puede agotar su tiempo.
                "HYT00", "Login timeout expired", "08S01", "Communication link failure")


def es_transitorio(error) -> bool:
    texto = str(error)
    return any(codigo in texto for codigo in TRANSITORIOS)


def activar(engine, intentos=10, espera=8.0, dormir=time.sleep):
    """Hasta `intentos` conexiones con `espera` segundos entre una y otra (~80 s en total)."""

    @event.listens_for(engine, "do_connect")
    def _conectar_con_reintento(dialect, conn_rec, cargs, cparams):
        for intento in range(1, intentos + 1):
            try:
                return dialect.connect(*cargs, **cparams)
            except Exception as e:  # noqa: BLE001 — se vuelve a lanzar si no es transitorio
                if intento == intentos or not es_transitorio(e):
                    raise
                dormir(espera)
