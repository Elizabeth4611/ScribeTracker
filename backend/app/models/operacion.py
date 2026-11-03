"""Modelos operativos: tiendas, rutas, asignaciones, jornadas, visitas,
evidencias, pausas, ubicaciones, incidencias, reportes y parámetros.

Los nombres de tablas y columnas siguen el diccionario de datos del ERS
(Apéndice 3). Donde el diccionario no alcanzaba para las reglas
confirmadas se agregaron tablas: Visita y Evidencia se separan (varias fotos
por visita), las pausas pasan de un TEXT a la tabla Pausa y las
asignaciones por fecha conservan el historial.
"""
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text

from app.extensions import db

ESTATUS_TIENDA = ("Activa", "Inactiva")
CATEGORIAS = ("Anaquel antes", "Anaquel después", "Precios", "Promociones")
TIPOS_PAUSA = ("Comida", "Descanso")
ESTADOS_INCIDENCIA = ("Pendiente", "Revisada", "Sancionada")


def _filtro(cond: str) -> dict:
    """Índice filtrado/parcial en SQL Server y SQLite."""
    return {"mssql_where": text(cond), "sqlite_where": text(cond)}


class Tienda(db.Model):
    __tablename__ = "Tienda"
    __table_args__ = (
        CheckConstraint("Estatus IN ('Activa', 'Inactiva')", name="CK_Tienda_Estatus"),
        CheckConstraint("Radio_Geocerca_Metros BETWEEN 10 AND 1000", name="CK_Tienda_Radio"),
        CheckConstraint("Latitud_Tienda BETWEEN -90 AND 90", name="CK_Tienda_Latitud"),
        CheckConstraint("Longitud_Tienda BETWEEN -180 AND 180", name="CK_Tienda_Longitud"),
    )

    id_tienda = db.Column("ID_Tienda", db.Integer, primary_key=True)
    nombre_comercial = db.Column("Nombre_Comercial", db.String(100), nullable=False)
    cadena = db.Column("Cadena", db.String(50), nullable=False)
    sucursal = db.Column("Sucursal", db.String(50), nullable=False)
    direccion_completa = db.Column("Direccion_Completa", db.String(255), nullable=False)
    zona = db.Column("Zona", db.String(50), nullable=True)
    latitud = db.Column("Latitud_Tienda", db.Numeric(10, 8), nullable=False)
    longitud = db.Column("Longitud_Tienda", db.Numeric(11, 8), nullable=False)
    radio_geocerca_m = db.Column(
        "Radio_Geocerca_Metros", db.Integer, nullable=False, default=50, server_default=text("50")
    )
    tiempo_estimado_min = db.Column("Tiempo_Estimado_Min", db.Integer, nullable=True)
    estatus = db.Column(
        "Estatus", db.String(20), nullable=False, default="Activa", server_default="Activa"
    )
    fecha_alta = db.Column("Fecha_Alta", db.DateTime, nullable=False)


class Ruta(db.Model):
    """Plantilla de ruta: tiendas en orden y días de la semana."""
    __tablename__ = "Ruta"
    __table_args__ = (
        CheckConstraint("Estado IN ('Activa', 'Inactiva')", name="CK_Ruta_Estado"),
    )

    id_ruta = db.Column("ID_Ruta", db.Integer, primary_key=True)
    nombre_ruta = db.Column("Nombre_Ruta", db.String(100), nullable=False)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    # Días como lista separada por comas: LUN,MAR,MIE,JUE,VIE,SAB,DOM
    dias_programados = db.Column("Dias_Programados", db.String(50), nullable=False)
    estado = db.Column("Estado", db.String(20), nullable=False, default="Activa", server_default="Activa")
    id_creado_por = db.Column("ID_Creado_Por", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    fecha_creacion = db.Column("Fecha_Creacion", db.DateTime, nullable=False)

    promotor = db.relationship("Usuario", foreign_keys=[id_promotor])
    tiendas = db.relationship(
        "RutaTienda", order_by="RutaTienda.orden_visita",
        cascade="all, delete-orphan", back_populates="ruta",
    )


class RutaTienda(db.Model):
    __tablename__ = "Ruta_Tienda"
    __table_args__ = (
        UniqueConstraint("ID_Ruta", "ID_Tienda", name="UQ_RutaTienda_Tienda"),
        UniqueConstraint("ID_Ruta", "Orden_Visita", name="UQ_RutaTienda_Orden"),
    )

    id_ruta_tienda = db.Column("ID_Ruta_Tienda", db.Integer, primary_key=True)
    id_ruta = db.Column("ID_Ruta", db.Integer, db.ForeignKey("Ruta.ID_Ruta"), nullable=False)
    id_tienda = db.Column("ID_Tienda", db.Integer, db.ForeignKey("Tienda.ID_Tienda"), nullable=False)
    orden_visita = db.Column("Orden_Visita", db.Integer, nullable=False)

    ruta = db.relationship("Ruta", back_populates="tiendas")
    tienda = db.relationship("Tienda")


class Asignacion(db.Model):
    """Tienda asignada a un promotor en una fecha y con un orden de visita.

    Nunca se borra: al quitarla se marca Cancelada para conservar historial.
    """
    __tablename__ = "Asignacion"
    __table_args__ = (
        CheckConstraint("Estado IN ('Activa', 'Cancelada')", name="CK_Asignacion_Estado"),
        Index("IX_Asignacion_Promotor_Fecha", "ID_Promotor", "Fecha"),
        Index(
            "UX_Asignacion_Activa", "ID_Promotor", "Fecha", "ID_Tienda",
            unique=True, **_filtro("Estado = 'Activa'"),
        ),
    )

    id_asignacion = db.Column("ID_Asignacion", db.Integer, primary_key=True)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    id_tienda = db.Column("ID_Tienda", db.Integer, db.ForeignKey("Tienda.ID_Tienda"), nullable=False)
    fecha = db.Column("Fecha", db.Date, nullable=False)
    orden_visita = db.Column("Orden_Visita", db.Integer, nullable=False)
    estado = db.Column("Estado", db.String(20), nullable=False, default="Activa", server_default="Activa")
    id_ruta = db.Column("ID_Ruta", db.Integer, db.ForeignKey("Ruta.ID_Ruta"), nullable=True)
    id_asignado_por = db.Column("ID_Asignado_Por", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    fecha_asignacion = db.Column("FechaHora_Asignacion", db.DateTime, nullable=False)
    fecha_cancelacion = db.Column("FechaHora_Cancelacion", db.DateTime, nullable=True)
    motivo_cancelacion = db.Column("Motivo_Cancelacion", db.String(200), nullable=True)

    tienda = db.relationship("Tienda")
    promotor = db.relationship("Usuario", foreign_keys=[id_promotor])


class Jornada(db.Model):
    __tablename__ = "Jornada"
    __table_args__ = (
        # Regla 1: una única jornada por promotor y fecha operativa.
        UniqueConstraint("ID_Promotor", "Fecha", name="UQ_Jornada_Promotor_Fecha"),
        CheckConstraint("Estado IN ('Abierta', 'Finalizada')", name="CK_Jornada_Estado"),
    )

    id_jornada = db.Column("ID_Jornada", db.Integer, primary_key=True)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    fecha = db.Column("Fecha", db.Date, nullable=False)
    fecha_hora_inicio = db.Column("FechaHora_Inicio", db.DateTime, nullable=False)
    fecha_hora_fin = db.Column("FechaHora_Fin", db.DateTime, nullable=True)
    latitud_inicio = db.Column("Latitud_Inicio", db.Numeric(10, 8), nullable=False)
    longitud_inicio = db.Column("Longitud_Inicio", db.Numeric(11, 8), nullable=False)
    precision_inicio_m = db.Column("Precision_Inicio_m", db.Float, nullable=True)
    id_tienda_inicio = db.Column("ID_Tienda_Inicio", db.Integer, db.ForeignKey("Tienda.ID_Tienda"), nullable=False)
    distancia_inicio_m = db.Column("Distancia_Inicio_m", db.Float, nullable=False)
    latitud_fin = db.Column("Latitud_Fin", db.Numeric(10, 8), nullable=True)
    longitud_fin = db.Column("Longitud_Fin", db.Numeric(11, 8), nullable=True)
    estado = db.Column("Estado", db.String(20), nullable=False, default="Abierta", server_default="Abierta")
    cierre_forzado = db.Column("Cierre_Forzado", db.Boolean, nullable=False, default=False, server_default=text("0"))
    motivo_cierre = db.Column("Motivo_Cierre", db.String(300), nullable=True)
    fecha_hora_recepcion = db.Column("FechaHora_Recepcion", db.DateTime, nullable=False)
    origen = db.Column("Origen", db.String(20), nullable=False, default="En línea", server_default="En línea")

    tienda_inicio = db.relationship("Tienda")
    pausas = db.relationship("Pausa", order_by="Pausa.fecha_hora_inicio", back_populates="jornada")
    visitas = db.relationship("Visita", order_by="Visita.fecha_hora_checkin", back_populates="jornada")


class Pausa(db.Model):
    __tablename__ = "Pausa"
    __table_args__ = (
        CheckConstraint("Tipo IN ('Comida', 'Descanso')", name="CK_Pausa_Tipo"),
        # Solo una pausa abierta a la vez por jornada.
        Index("UX_Pausa_Abierta", "ID_Jornada", unique=True, **_filtro("FechaHora_Fin IS NULL")),
    )

    id_pausa = db.Column("ID_Pausa", db.Integer, primary_key=True)
    id_jornada = db.Column("ID_Jornada", db.Integer, db.ForeignKey("Jornada.ID_Jornada"), nullable=False)
    tipo = db.Column("Tipo", db.String(20), nullable=False)
    fecha_hora_inicio = db.Column("FechaHora_Inicio", db.DateTime, nullable=False)
    fecha_hora_fin = db.Column("FechaHora_Fin", db.DateTime, nullable=True)
    duracion_programada_min = db.Column("Duracion_Programada_Min", db.Integer, nullable=False)

    jornada = db.relationship("Jornada", back_populates="pausas")


class Visita(db.Model):
    """Registro de visita (check-in / check-out). Las fotos van en Evidencia."""
    __tablename__ = "Visita"
    __table_args__ = (
        CheckConstraint("Estado IN ('Abierta', 'Cerrada')", name="CK_Visita_Estado"),
        # Regla 9: nunca dos visitas abiertas del mismo promotor.
        Index("UX_Visita_Abierta_Promotor", "ID_Promotor", unique=True, **_filtro("Estado = 'Abierta'")),
        # Una sola visita por tienda asignada.
        UniqueConstraint("ID_Asignacion", name="UQ_Visita_Asignacion"),
        Index("UX_Visita_Cliente", "ID_Cliente", unique=True, **_filtro("ID_Cliente IS NOT NULL")),
    )

    id_visita = db.Column("ID_Registro_Visita", db.Integer, primary_key=True)
    id_jornada = db.Column("ID_Jornada", db.Integer, db.ForeignKey("Jornada.ID_Jornada"), nullable=False)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    id_tienda = db.Column("ID_Tienda", db.Integer, db.ForeignKey("Tienda.ID_Tienda"), nullable=False)
    id_asignacion = db.Column("ID_Asignacion", db.Integer, db.ForeignKey("Asignacion.ID_Asignacion"), nullable=False)
    id_cliente = db.Column("ID_Cliente", db.String(36), nullable=True)
    estado = db.Column("Estado", db.String(20), nullable=False, default="Abierta", server_default="Abierta")

    fecha_hora_checkin = db.Column("FechaHora_CheckIn", db.DateTime, nullable=False)
    latitud_checkin = db.Column("Latitud_CheckIn", db.Numeric(10, 8), nullable=False)
    longitud_checkin = db.Column("Longitud_CheckIn", db.Numeric(11, 8), nullable=False)
    precision_checkin_m = db.Column("Precision_CheckIn_m", db.Float, nullable=True)
    distancia_checkin_m = db.Column("Distancia_CheckIn_m", db.Float, nullable=False)
    recepcion_checkin = db.Column("FechaHora_Recepcion_CheckIn", db.DateTime, nullable=False)

    fecha_hora_checkout = db.Column("FechaHora_CheckOut", db.DateTime, nullable=True)
    latitud_checkout = db.Column("Latitud_CheckOut", db.Numeric(10, 8), nullable=True)
    longitud_checkout = db.Column("Longitud_CheckOut", db.Numeric(11, 8), nullable=True)
    precision_checkout_m = db.Column("Precision_CheckOut_m", db.Float, nullable=True)
    distancia_checkout_m = db.Column("Distancia_CheckOut_m", db.Float, nullable=True)
    recepcion_checkout = db.Column("FechaHora_Recepcion_CheckOut", db.DateTime, nullable=True)
    origen = db.Column("Origen", db.String(20), nullable=False, default="En línea", server_default="En línea")

    jornada = db.relationship("Jornada", back_populates="visitas")
    tienda = db.relationship("Tienda")
    promotor = db.relationship("Usuario", foreign_keys=[id_promotor])
    evidencias = db.relationship("Evidencia", order_by="Evidencia.fecha_hora_captura", back_populates="visita")


class Evidencia(db.Model):
    __tablename__ = "Evidencia"
    __table_args__ = (
        CheckConstraint(
            "Categoria IN ('Anaquel antes', 'Anaquel después', 'Precios', 'Promociones')",
            name="CK_Evidencia_Categoria",
        ),
        CheckConstraint(
            "Estatus_Validacion IN ('Válida', 'Fuera de geocerca', 'Rechazada')",
            name="CK_Evidencia_Estatus",
        ),
        CheckConstraint(
            "Revision_Supervisor IN ('Sin revisar', 'Aprobada', 'Observada')",
            name="CK_Evidencia_Revision",
        ),
        Index("IX_Evidencia_Hash", "Hash_Imagen"),
        Index("UX_Evidencia_Cliente", "ID_Cliente", unique=True, **_filtro("ID_Cliente IS NOT NULL")),
    )

    id_evidencia = db.Column("ID_Evidencia", db.Integer, primary_key=True)
    id_visita = db.Column("ID_Registro_Visita", db.Integer, db.ForeignKey("Visita.ID_Registro_Visita"), nullable=False)
    id_cliente = db.Column("ID_Cliente", db.String(36), nullable=True)
    categoria = db.Column("Categoria", db.String(30), nullable=False)
    sin_promocion = db.Column("Sin_Promocion", db.Boolean, nullable=False, default=False, server_default=text("0"))
    ruta_imagen = db.Column("Ruta_Imagen", db.String(255), nullable=False)
    hash_imagen = db.Column("Hash_Imagen", db.String(64), nullable=False)
    metadatos_imagen = db.Column("Metadatos_Imagen", db.Text, nullable=False)
    fecha_hora_captura = db.Column("FechaHora_Captura", db.DateTime, nullable=False)
    fecha_hora_recepcion = db.Column("FechaHora_Recepcion", db.DateTime, nullable=False)
    latitud = db.Column("Latitud", db.Numeric(10, 8), nullable=False)
    longitud = db.Column("Longitud", db.Numeric(11, 8), nullable=False)
    precision_m = db.Column("Precision_m", db.Float, nullable=True)
    distancia_m = db.Column("Distancia_m", db.Float, nullable=False)
    dentro_geocerca = db.Column("Dentro_Geocerca", db.Boolean, nullable=False)
    estatus_validacion = db.Column("Estatus_Validacion", db.String(20), nullable=False)
    motivo_validacion = db.Column("Motivo_Validacion", db.String(200), nullable=True)
    revision_supervisor = db.Column(
        "Revision_Supervisor", db.String(20), nullable=False,
        default="Sin revisar", server_default="Sin revisar",
    )
    id_revisor = db.Column("ID_Revisor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=True)
    comentario_revision = db.Column("Comentario_Revision", db.String(300), nullable=True)
    origen = db.Column("Origen", db.String(20), nullable=False, default="En línea", server_default="En línea")

    visita = db.relationship("Visita", back_populates="evidencias")


class Ubicacion(db.Model):
    """Punto de seguimiento periódico (RF-02)."""
    __tablename__ = "Ubicacion"
    __table_args__ = (
        Index("IX_Ubicacion_Promotor_Fecha", "ID_Promotor", "FechaHora_Captura"),
        Index("UX_Ubicacion_Cliente", "ID_Cliente", unique=True, **_filtro("ID_Cliente IS NOT NULL")),
    )

    id_ubicacion = db.Column("ID_Ubicacion", db.Integer, primary_key=True)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    id_jornada = db.Column("ID_Jornada", db.Integer, db.ForeignKey("Jornada.ID_Jornada"), nullable=False)
    id_cliente = db.Column("ID_Cliente", db.String(36), nullable=True)
    latitud = db.Column("Latitud", db.Numeric(10, 8), nullable=False)
    longitud = db.Column("Longitud", db.Numeric(11, 8), nullable=False)
    precision_m = db.Column("Precision_m", db.Float, nullable=True)
    fecha_hora_captura = db.Column("FechaHora_Captura", db.DateTime, nullable=False)
    fecha_hora_recepcion = db.Column("FechaHora_Recepcion", db.DateTime, nullable=False)
    origen = db.Column("Origen", db.String(20), nullable=False, default="En línea", server_default="En línea")


class Incidencia(db.Model):
    __tablename__ = "Incidencia"
    __table_args__ = (
        CheckConstraint(
            "Estado_Incidencia IN ('Pendiente', 'Revisada', 'Sancionada')",
            name="CK_Incidencia_Estado",
        ),
        Index("IX_Incidencia_Promotor_Fecha", "ID_Promotor", "Fecha_Hora"),
        Index("UX_Incidencia_Clave", "Clave_Unica", unique=True, **_filtro("Clave_Unica IS NOT NULL")),
    )

    id_incidencia = db.Column("ID_Incidencia", db.Integer, primary_key=True)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    tipo = db.Column("Tipo_Incidencia", db.String(50), nullable=False)
    es_critica = db.Column("Es_Critica", db.Boolean, nullable=False, default=False, server_default=text("0"))
    fecha_hora = db.Column("Fecha_Hora", db.DateTime, nullable=False)
    descripcion = db.Column("Descripcion", db.Text, nullable=True)
    estado = db.Column(
        "Estado_Incidencia", db.String(20), nullable=False, default="Pendiente", server_default="Pendiente"
    )
    id_jornada = db.Column("ID_Jornada", db.Integer, db.ForeignKey("Jornada.ID_Jornada"), nullable=True)
    id_visita = db.Column("ID_Registro_Visita", db.Integer, db.ForeignKey("Visita.ID_Registro_Visita"), nullable=True)
    id_evidencia = db.Column("ID_Evidencia", db.Integer, db.ForeignKey("Evidencia.ID_Evidencia"), nullable=True)
    # Clave para no repetir la misma alerta automática (p. ej. "inactividad:15").
    clave_unica = db.Column("Clave_Unica", db.String(100), nullable=True)
    origen = db.Column("Origen", db.String(20), nullable=False, default="Sistema", server_default="Sistema")
    id_reporto = db.Column("ID_Reporto", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=True)
    id_revisor = db.Column("ID_Revisor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=True)
    fecha_hora_revision = db.Column("FechaHora_Revision", db.DateTime, nullable=True)
    comentario_revision = db.Column("Comentario_Revision", db.String(300), nullable=True)

    promotor = db.relationship("Usuario", foreign_keys=[id_promotor])


class Reporte(db.Model):
    __tablename__ = "Reporte"
    __table_args__ = (
        CheckConstraint("Tipo_Reporte IN ('Diario', 'Semanal', 'Mensual')", name="CK_Reporte_Tipo"),
        CheckConstraint("Formato IN ('PDF', 'Excel')", name="CK_Reporte_Formato"),
        CheckConstraint(
            "Contenido IN ('Desempeño', 'Incidencias', 'Exhibición')", name="CK_Reporte_Contenido"
        ),
    )

    id_reporte = db.Column("ID_Reporte", db.Integer, primary_key=True)
    tipo = db.Column("Tipo_Reporte", db.String(20), nullable=False)
    contenido = db.Column("Contenido", db.String(20), nullable=False)
    fecha_generacion = db.Column("Fecha_Generacion", db.DateTime, nullable=False)
    fecha_inicio = db.Column("Fecha_Inicio", db.Date, nullable=False)
    fecha_fin = db.Column("Fecha_Fin", db.Date, nullable=False)
    id_promotor = db.Column("ID_Promotor", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=True)
    id_generado_por = db.Column("ID_Generado_Por", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    metricas = db.Column("Metricas", db.Text, nullable=False)
    formato = db.Column("Formato", db.String(10), nullable=False, default="PDF", server_default="PDF")


class Parametro(db.Model):
    __tablename__ = "Parametro"

    id_parametro = db.Column("ID_Parametro", db.Integer, primary_key=True)
    clave = db.Column("Clave", db.String(50), unique=True, nullable=False)
    descripcion = db.Column("Descripcion", db.String(200), nullable=False)
    tipo_dato = db.Column("Tipo_Dato", db.String(20), nullable=False)
    valor_activo = db.Column("Valor_Activo", db.String(50), nullable=False)
    valor_default = db.Column("Valor_Default", db.String(50), nullable=False)
    rango = db.Column("Rango", db.String(50), nullable=True)
    categoria = db.Column("Categoria", db.String(50), nullable=False)
    fecha_modificacion = db.Column("Fecha_Modificacion", db.DateTime, nullable=False)


class EventoCliente(db.Model):
    """Idempotencia: cada acción del promotor lleva un ID generado en el
    dispositivo. Si llega dos veces (reintento o sincronización), se devuelve
    la respuesta guardada sin volver a ejecutarla."""
    __tablename__ = "Evento_Cliente"
    __table_args__ = (
        UniqueConstraint("ID_Usuario", "ID_Cliente", name="UQ_Evento_Usuario_Cliente"),
    )

    id_evento = db.Column("ID_Evento", db.Integer, primary_key=True)
    id_usuario = db.Column("ID_Usuario", db.Integer, db.ForeignKey("Usuario.ID_Usuario"), nullable=False)
    id_cliente = db.Column("ID_Cliente", db.String(36), nullable=False)
    tipo = db.Column("Tipo", db.String(30), nullable=False)
    fecha_hora_captura = db.Column("FechaHora_Captura", db.DateTime, nullable=True)
    fecha_hora_recepcion = db.Column("FechaHora_Recepcion", db.DateTime, nullable=False)
    codigo_http = db.Column("Codigo_HTTP", db.Integer, nullable=False)
    respuesta = db.Column("Respuesta", db.Text, nullable=False)
