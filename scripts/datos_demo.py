"""Datos de demostración (no borra ni modifica datos existentes de negocio).

- Crea 4 tiendas en León, Gto., si no existen (nombre + sucursal).
- Asigna número de empleado a los usuarios de prueba que no lo tengan.
- Asigna a promotor.prueba@scribetracker.test las 4 tiendas para HOY si no
  tiene asignaciones ese día, y crea una ruta plantilla de lunes a viernes.
Imprime las coordenadas para simular la ubicación en Chrome (Sensores).
"""
import os
import sys
from datetime import datetime

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))
os.chdir(BACKEND)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Asignacion, Ruta, RutaTienda, Tienda, Usuario  # noqa: E402
from app.servicios import parametros  # noqa: E402

TIENDAS = [
    ("Walmart", "Walmart", "Torres Landa", "Blvd. Juan Alonso de Torres 2002, León", "Norte", 21.1458, -101.6893, 90, 150),
    ("Soriana", "Soriana", "San Juan Bosco", "Blvd. San Juan Bosco 3802, León", "Poniente", 21.1395, -101.7104, 80, 90),
    ("Office Depot", "Office Depot", "Altacia", "Blvd. Aeropuerto 104, Plaza Altacia, León", "Oriente", 21.1028, -101.6280, 60, 60),
    ("Bodega Aurrera", "Walmart", "López Mateos", "Blvd. Adolfo López Mateos 1501, León", "Centro", 21.1213, -101.6740, 70, 120),
]
PRUEBA = {"admin.prueba@scribetracker.test": "PRU-ADM", "supervisor.prueba@scribetracker.test": "PRU-SUP",
          "promotor.prueba@scribetracker.test": "PRU-001", "inactivo.prueba@scribetracker.test": "PRU-002"}

app = create_app()
with app.app_context():
    parametros.sembrar()
    tiendas = []
    for nom, cad, suc, dirc, zona, lat, lon, radio, minutos in TIENDAS:
        t = db.session.execute(db.select(Tienda).where(Tienda.nombre_comercial == nom, Tienda.sucursal == suc)).scalar_one_or_none()
        if t is None:
            t = Tienda(nombre_comercial=nom, cadena=cad, sucursal=suc, direccion_completa=dirc, zona=zona, latitud=lat,
                       longitud=lon, radio_geocerca_m=radio, tiempo_estimado_min=minutos, estatus="Activa", fecha_alta=datetime.now())
            db.session.add(t)
            print(f"Tienda creada: {nom} {suc}")
        tiendas.append(t)
    for correo, num in PRUEBA.items():
        u = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == correo)).scalar_one_or_none()
        if u and not u.numero_empleado:
            u.numero_empleado = num
            u.telefono = u.telefono or "4770000000"
            u.tipo_contrato = "Temporada" if u.rol == "Promotor" else None
            u.fecha_alta = u.fecha_alta or datetime.now()
    db.session.commit()

    p = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "promotor.prueba@scribetracker.test")).scalar_one_or_none()
    s = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "supervisor.prueba@scribetracker.test")).scalar_one_or_none()
    if p and s:
        hoy = datetime.now().date()
        ya = db.session.execute(db.select(Asignacion).where(Asignacion.id_promotor == p.id_usuario, Asignacion.fecha == hoy,
                                                            Asignacion.estado == "Activa")).first()
        if not ya:
            for i, t in enumerate(tiendas, 1):
                db.session.add(Asignacion(id_promotor=p.id_usuario, id_tienda=t.id_tienda, fecha=hoy, orden_visita=i,
                                          estado="Activa", id_asignado_por=s.id_usuario, fecha_asignacion=datetime.now()))
            print(f"Asignadas {len(tiendas)} tiendas a {p.nombre_completo} para {hoy}")
        if not db.session.execute(db.select(Ruta).where(Ruta.id_promotor == p.id_usuario)).first():
            r = Ruta(nombre_ruta="León Demo", id_promotor=p.id_usuario, dias_programados="LUN,MAR,MIE,JUE,VIE",
                     estado="Activa", id_creado_por=s.id_usuario, fecha_creacion=datetime.now())
            r.tiendas = [RutaTienda(id_tienda=t.id_tienda, orden_visita=i) for i, t in enumerate(tiendas, 1)]
            db.session.add(r)
        db.session.commit()
    print("\nCoordenadas para simular la ubicación (Chrome > DevTools > Sensores > Ubicación):")
    for t in tiendas:
        print(f"  {t.nombre_comercial} {t.sucursal}: latitud {float(t.latitud)}, longitud {float(t.longitud)} (radio {t.radio_geocerca_m} m)")
