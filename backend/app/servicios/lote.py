"""Consultas en lote para el panel del supervisor (corrección F13, desempeño).

El mapa en tiempo real hacía ~20 consultas por promotor (más de 1,400 con 70
promotores) y tardaba ~10 s en SQL Server, contra el límite de 5 s de RF-10.
Aquí se cargan los datos del día de TODOS los promotores con pocas consultas
y luego se calcula cada estado en memoria con las mismas reglas.
"""
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Asignacion, Jornada, Pausa, Tienda, Ubicacion, Visita


class Contexto:
    def __init__(self, ids: list[int], fecha):
        self.fecha = fecha
        ids = list(ids) or [-1]
        self.asignaciones: dict[int, list[Asignacion]] = {i: [] for i in ids}
        for a in db.session.execute(
                db.select(Asignacion).join(Tienda).options(selectinload(Asignacion.tienda)).where(
                    Asignacion.id_promotor.in_(ids), Asignacion.fecha == fecha, Asignacion.estado == "Activa")
                .order_by(Asignacion.id_promotor, Asignacion.orden_visita)).scalars():
            self.asignaciones[a.id_promotor].append(a)
        self.jornadas: dict[int, Jornada] = {j.id_promotor: j for j in db.session.execute(
            db.select(Jornada).options(selectinload(Jornada.pausas), selectinload(Jornada.visitas))
            .where(Jornada.id_promotor.in_(ids), Jornada.fecha == fecha)).scalars()}
        ids_j = [j.id_jornada for j in self.jornadas.values()] or [-1]
        self.pausa_activa: dict[int, Pausa] = {p.id_jornada: p for p in db.session.execute(
            db.select(Pausa).where(Pausa.id_jornada.in_(ids_j), Pausa.fecha_hora_fin.is_(None))).scalars()}
        self.visita_abierta: dict[int, Visita] = {v.id_promotor: v for v in db.session.execute(
            db.select(Visita).options(selectinload(Visita.tienda))
            .where(Visita.id_promotor.in_(ids), Visita.estado == "Abierta")).scalars()}
        ids_a = [a.id_asignacion for lst in self.asignaciones.values() for a in lst] or [-1]
        self.visita_de_asignacion: dict[int, Visita] = {v.id_asignacion: v for v in db.session.execute(
            db.select(Visita).where(Visita.id_asignacion.in_(ids_a))).scalars()}
        ultima = (db.select(Ubicacion.id_jornada, func.max(Ubicacion.fecha_hora_captura).label("max"))
                  .where(Ubicacion.id_jornada.in_(ids_j)).group_by(Ubicacion.id_jornada).subquery())
        self.ultima_ubicacion: dict[int, Ubicacion] = {}
        for u in db.session.execute(db.select(Ubicacion).join(
                ultima, (Ubicacion.id_jornada == ultima.c.id_jornada) & (Ubicacion.fecha_hora_captura == ultima.c.max))
                .order_by(Ubicacion.id_ubicacion)).scalars():
            self.ultima_ubicacion[u.id_jornada] = u   # si hay empate, gana la última registrada
