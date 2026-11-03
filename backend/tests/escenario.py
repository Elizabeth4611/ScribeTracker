"""Escenario de datos para las pruebas de operación.

Tiendas ficticias alrededor de León, Gto. Separación aproximada de 1-2 km
entre ellas y radio de geocerca de 50 m.
"""
import io
import os
import uuid
from datetime import date, datetime

from app.extensions import db
from app.models import Asignacion, Tienda, Usuario
from app.servicios import tiempo
from tests.conftest import PASSWORD

M_LAT = 1 / 111_320  # grados de latitud por metro

TIENDAS = [
    ("Walmart", "Walmart", "Torres Landa", 21.1250, -101.6800, "Norte"),
    ("Soriana", "Soriana", "San Juan Bosco", 21.1350, -101.6800, "Norte"),
    ("Office Depot", "Office Depot", "Altacia", 21.1450, -101.6800, "Norte"),
    ("Bodega Aurrera", "Walmart", "López Mateos", 21.1100, -101.6600, "Centro"),
]


def crear_usuario(nombre, correo, rol, sup=None, estatus="Activo", numero=None):
    u = Usuario(nombre_completo=nombre, correo_electronico=correo, rol=rol, estatus=estatus,
                id_supervisor=sup.id_usuario if sup else None,
                numero_empleado=numero or uuid.uuid4().hex[:8].upper(), telefono="4771234567")
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u


def crear_tiendas():
    ts = []
    for nombre, cadena, suc, lat, lon, zona in TIENDAS:
        t = Tienda(nombre_comercial=nombre, cadena=cadena, sucursal=suc, direccion_completa="Dirección de prueba",
                   zona=zona, latitud=lat, longitud=lon, radio_geocerca_m=50, estatus="Activa",
                   fecha_alta=datetime(2026, 1, 1))
        db.session.add(t)
        ts.append(t)
    db.session.commit()
    return ts


def asignar(promotor, tiendas, fecha, por):
    for i, t in enumerate(tiendas, 1):
        db.session.add(Asignacion(id_promotor=promotor.id_usuario, id_tienda=t.id_tienda, fecha=fecha,
                                  orden_visita=i, estado="Activa", id_asignado_por=por.id_usuario,
                                  fecha_asignacion=datetime(2026, 1, 1)))
    db.session.commit()


def punto(tienda_o_coord, metros_norte=0.0):
    """Coordenada desplazada N metros al norte de una tienda."""
    lat, lon = (float(tienda_o_coord.latitud), float(tienda_o_coord.longitud)) \
        if hasattr(tienda_o_coord, "latitud") else tienda_o_coord
    return {"latitud": lat + metros_norte * M_LAT, "longitud": lon, "precision": 10}


def foto(tamano=200):
    """Bytes de una imagen JPEG mínima con contenido único (hash distinto)."""
    return b"\xff\xd8\xff\xe0" + os.urandom(tamano)


def subir_foto(client, id_visita, categoria, coord, datos=None, cabeceras=None, sin_promocion=False, captura=None):
    form = {"categoria": categoria, "id_visita": str(id_visita), **{k: str(v) for k, v in coord.items()},
            "metadatos": '{"fuente": "camara"}', "foto": (io.BytesIO(datos or foto()), "captura.jpg")}
    if sin_promocion:
        form["sin_promocion"] = "1"
    if captura:
        form["capturado_en"] = captura
    return client.post("/api/promotor/evidencias", data=form, content_type="multipart/form-data",
                       headers=cabeceras or {})


HOY = date(2026, 11, 4)


def a_las(h, m=0):
    tiempo.fijar(datetime(HOY.year, HOY.month, HOY.day, h, m))
