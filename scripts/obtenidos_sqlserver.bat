@echo off
rem Ejecuta en una sola sesion los casos del reporte contra SQL Server (base de pruebas)
rem y guarda el resultado obtenido de cada uno (record_property) en un XML JUnit.
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
set ST_BD_PRUEBAS=ScribeTracker_Pruebas
echo Inicio: %DATE% %TIME% > "%~dp0logs\obtenidos_sqlserver.log"
python -m pytest tests/test_auth.py::test_login_correcto_devuelve_rol_sin_hash tests/test_usuarios.py::test_U10_contrasena_temporal_obliga_cambio tests/test_jornada.py::test_J07_flujo_completo tests/test_supervision_reportes.py::test_S01_mapa_y_alcance_supervisor tests/test_supervision_reportes.py::test_S02_ubicacion_desactualizada tests/test_supervision_reportes.py::test_REP02_pdf_y_permisos tests/test_auth.py::test_matriz_de_permisos tests/test_auth.py::test_usuario_inactivo_no_entra tests/test_usuarios.py::test_U05_solo_admin_gestiona tests/test_usuarios.py::test_U02_campos_obligatorios tests/test_usuarios.py::test_U03_duplicados tests/test_jornada.py::test_A01_promotor_no_accede_a_registros_ajenos tests/test_tiendas_rutas.py::test_R03_supervisor_fuera_de_alcance tests/test_jornada.py::test_J01_inicio_en_primera_tienda tests/test_jornada.py::test_J02_inicio_fuera_de_primera_tienda tests/test_jornada.py::test_J03_jornada_unica_por_fecha tests/test_jornada.py::test_V01_checkin_independiente_del_inicio tests/test_jornada.py::test_V03_dos_visitas_abiertas tests/test_jornada.py::test_E02_foto_fuera_de_geocerca_no_cuenta tests/test_jornada.py::test_V04_checkout_bloqueado_por_categorias tests/test_jornada.py::test_V05_checkout_valido_no_cierra_jornada tests/test_jornada.py::test_J06_finalizar_con_pendientes tests/test_jornada.py::test_P02_rastreo_suspendido_en_pausa_y_tras_cierre tests/test_supervision_reportes.py::test_O01_reintento_sin_duplicados tests/test_supervision_reportes.py::test_REP01_reporte_consistente_con_registros tests/test_tiendas_rutas.py::test_T02_coordenadas_obligatorias -v -o junit_family=legacy --junitxml="%~dp0..\docs\evidencias\salidas\obtenidos_sqlserver.xml" >> "%~dp0logs\obtenidos_sqlserver.log" 2>&1
echo Codigo de salida: %ERRORLEVEL% >> "%~dp0logs\obtenidos_sqlserver.log"
echo Fin: %DATE% %TIME% >> "%~dp0logs\obtenidos_sqlserver.log"
echo === FIN === >> "%~dp0logs\obtenidos_sqlserver.log"
endlocal
