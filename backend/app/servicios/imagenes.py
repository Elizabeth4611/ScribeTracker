"""Validación y guardado de fotografías (evidencias y foto de inicio de jornada).

Se revisa el contenido real del archivo (firma JPEG, PNG o WEBP), el tamaño
y que la misma imagen no se haya enviado antes (hash SHA-256). Esto detecta
fotos repetidas; no detecta imágenes generadas por IA.
"""
import hashlib
import os
import uuid

from flask import current_app

FIRMAS = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"), b"\x89PNG\r\n\x1a\n": ("image/png", ".png")}


class ImagenError(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje, self.codigo = mensaje, codigo


def tipo_imagen(datos: bytes):
    for firma, tipo in FIRMAS.items():
        if datos.startswith(firma):
            return tipo
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return ("image/webp", ".webp")
    return None


def leer(archivo) -> tuple[bytes, tuple[str, str], str]:
    """Devuelve (bytes, (mime, extensión), sha256) o lanza ImagenError."""
    if archivo is None:
        raise ImagenError("No se recibió la fotografía.")
    datos = archivo.read()
    if not datos:
        raise ImagenError("La fotografía está vacía.")
    if len(datos) > current_app.config["EVIDENCIA_MAX_BYTES"]:
        raise ImagenError("La fotografía supera los 5 MB.", 413)
    tipo = tipo_imagen(datos)
    if tipo is None:
        raise ImagenError("El archivo no es una imagen JPEG, PNG o WEBP.")
    return datos, tipo, hashlib.sha256(datos).hexdigest()


def ya_usada(sha: str) -> bool:
    """La imagen ya se envió antes como evidencia válida o como foto de inicio."""
    from app.extensions import db
    from app.models import Evidencia, Jornada
    if db.session.execute(db.select(Evidencia.id_evidencia).where(
            Evidencia.hash_imagen == sha, Evidencia.estatus_validacion != "Rechazada")).first():
        return True
    return db.session.execute(db.select(Jornada.id_jornada).where(Jornada.foto_inicio_hash == sha)).first() is not None


def guardar(datos: bytes, extension: str, momento, subcarpeta: str = "") -> str:
    """Guarda con nombre aleatorio (nunca el del cliente). Devuelve la ruta relativa con '/'."""
    rel = os.path.join(*(p for p in (subcarpeta, momento.strftime("%Y"), momento.strftime("%m")) if p),
                       f"{uuid.uuid4().hex}{extension}")
    destino = os.path.join(current_app.config["EVIDENCIAS_DIR"], rel)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as fh:
        fh.write(datos)
    return rel.replace(os.sep, "/")
