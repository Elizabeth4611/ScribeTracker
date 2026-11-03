"""Casos de prueba del reporte (docs/REPORTE_PRUEBAS.md).

CP-01 a CP-07: fallos reales encontrados (F01-F07), con evidencia antes y después.
CP-08 en adelante: validaciones y flujos que pasaron (incluye rechazos esperados).
"""
CASOS = [
    # id, fallo, nombre, archivo::prueba (vacío = no es prueba pytest)
    ("CP-01", "F01", "Login no expone contraseña ni hash", "tests/test_auth.py::test_login_correcto_devuelve_rol_sin_hash"),
    ("CP-02", "F02", "Contraseña temporal obliga a cambiarla", "tests/test_usuarios.py::test_U10_contrasena_temporal_obliga_cambio"),
    ("CP-03", "F03", "Flujo completo de jornada con dos tiendas", "tests/test_jornada.py::test_J07_flujo_completo"),
    ("CP-04", "F04", "Mapa y alcance del supervisor", "tests/test_supervision_reportes.py::test_S01_mapa_y_alcance_supervisor"),
    ("CP-05", "F05", "Ubicación reciente y desactualizada", "tests/test_supervision_reportes.py::test_S02_ubicacion_desactualizada"),
    ("CP-06", "F06", "Exportar reporte de exhibición a PDF", "tests/test_supervision_reportes.py::test_REP02_pdf_y_permisos"),
    ("CP-07", "F07", "Sincronización de eventos sin conexión (Angular)", ""),
    ("CP-08", "", "Acceso por rol (matriz de permisos)", "tests/test_auth.py::test_matriz_de_permisos"),
    ("CP-09", "", "Rechazo de cuenta inactiva", "tests/test_auth.py::test_usuario_inactivo_no_entra"),
    ("CP-10", "", "Petición manipulada: solo el administrador registra usuarios", "tests/test_usuarios.py::test_U05_solo_admin_gestiona"),
    ("CP-11", "", "Campos obligatorios en el alta de usuarios", "tests/test_usuarios.py::test_U02_campos_obligatorios"),
    ("CP-12", "", "Correo y número de empleado duplicados", "tests/test_usuarios.py::test_U03_duplicados"),
    ("CP-13", "", "Promotor sin acceso a registros ajenos", "tests/test_jornada.py::test_A01_promotor_no_accede_a_registros_ajenos"),
    ("CP-14", "", "Supervisor limitado a su ámbito", "tests/test_tiendas_rutas.py::test_R03_supervisor_fuera_de_alcance"),
    ("CP-15", "", "Inicio de jornada en la primera tienda", "tests/test_jornada.py::test_J01_inicio_en_primera_tienda"),
    ("CP-16", "", "Rechazo de inicio fuera de la primera tienda", "tests/test_jornada.py::test_J02_inicio_fuera_de_primera_tienda"),
    ("CP-17", "", "Una sola jornada por fecha", "tests/test_jornada.py::test_J03_jornada_unica_por_fecha"),
    ("CP-18", "", "Check-in separado del inicio de jornada", "tests/test_jornada.py::test_V01_checkin_independiente_del_inicio"),
    ("CP-19", "", "Dos visitas abiertas y visita duplicada", "tests/test_jornada.py::test_V03_dos_visitas_abiertas"),
    ("CP-20", "", "Foto fuera de geocerca no cuenta", "tests/test_jornada.py::test_E02_foto_fuera_de_geocerca_no_cuenta"),
    ("CP-21", "", "Check-out bloqueado por categorías faltantes", "tests/test_jornada.py::test_V04_checkout_bloqueado_por_categorias"),
    ("CP-22", "", "Check-out válido sin cerrar la jornada", "tests/test_jornada.py::test_V05_checkout_valido_no_cierra_jornada"),
    ("CP-23", "", "Cierre de jornada con visitas pendientes", "tests/test_jornada.py::test_J06_finalizar_con_pendientes"),
    ("CP-24", "", "Seguimiento suspendido en pausa y tras el cierre", "tests/test_jornada.py::test_P02_rastreo_suspendido_en_pausa_y_tras_cierre"),
    ("CP-25", "", "Reintentos sin duplicados", "tests/test_supervision_reportes.py::test_O01_reintento_sin_duplicados"),
    ("CP-26", "", "Reporte consistente con los registros", "tests/test_supervision_reportes.py::test_REP01_reporte_consistente_con_registros"),
    ("CP-27", "", "Coordenadas obligatorias de tienda", "tests/test_tiendas_rutas.py::test_T02_coordenadas_obligatorias"),
]
