"""Etapa 3 · Prueba de DESEMPEÑO (unidad) del mapa del supervisor · F13.

La medición completa con SQL Server y 70 promotores está en
scripts/pruebas_sistema.bat (RF-10: < 5 s). Esta prueba fija la causa del
defecto F13: el número de consultas SQL no debe crecer con cada promotor.
"""
from datetime import datetime

from sqlalchemy import event

from app.extensions import db
from app.models import Asignacion, Jornada, Tienda, Ubicacion, Usuario
from tests.conftest import PASSWORD

N = 70


def test_DES01_mapa_con_70_promotores_usa_pocas_consultas(app, client):
    with app.app_context():
        sup = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "supervisor@test.mx")).scalar_one()
        t = Tienda(nombre_comercial="Walmart", cadena="Walmart", sucursal="Prueba", direccion_completa="León",
                   zona="Centro", latitud=21.1458, longitud=-101.6893, radio_geocerca_m=100, tiempo_estimado_min=60,
                   estatus="Activa", fecha_alta=datetime.now())
        db.session.add(t)
        db.session.flush()
        hoy = datetime.now().date()
        for i in range(N):
            p = Usuario(nombre_completo=f"Promotor {i:02d}", correo_electronico=f"carga{i}@test.mx", rol="Promotor",
                        id_supervisor=sup.id_usuario)
            p.set_password(PASSWORD)
            db.session.add(p)
            db.session.flush()
            db.session.add(Asignacion(id_promotor=p.id_usuario, id_tienda=t.id_tienda, fecha=hoy, orden_visita=1,
                                      estado="Activa", id_asignado_por=sup.id_usuario, fecha_asignacion=datetime.now()))
            j = Jornada(id_promotor=p.id_usuario, fecha=hoy, fecha_hora_inicio=datetime.now(), latitud_inicio=21.1458,
                        longitud_inicio=-101.6893, id_tienda_inicio=t.id_tienda, distancia_inicio_m=5, estado="Abierta",
                        fecha_hora_recepcion=datetime.now())
            db.session.add(j)
            db.session.flush()
            db.session.add(Ubicacion(id_promotor=p.id_usuario, id_jornada=j.id_jornada, latitud=21.1458,
                                     longitud=-101.6893, fecha_hora_captura=datetime.now(), fecha_hora_recepcion=datetime.now()))
        db.session.commit()
        motor = db.engine
    client.post("/api/auth/login", json={"usuario": "supervisor@test.mx", "password": PASSWORD})
    consultas = []
    escuchar = lambda *a, **k: consultas.append(1)  # noqa: E731
    event.listen(motor, "before_cursor_execute", escuchar)
    try:
        r = client.get("/api/supervision/mapa")
    finally:
        event.remove(motor, "before_cursor_execute", escuchar)
    assert r.status_code == 200 and len(r.get_json()["promotores"]) >= N
    print(f"\n    GET /api/supervision/mapa con {N} promotores: {len(consultas)} consultas SQL")
    assert len(consultas) <= 60, f"{len(consultas)} consultas SQL (antes de F13 eran ~1,200)"
