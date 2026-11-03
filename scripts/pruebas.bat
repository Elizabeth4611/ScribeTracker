@echo off
rem ============================================================
rem  Ejecuta todas las pruebas automáticas del backend:
rem   1) contra SQL Server, en la base SEPARADA ScribeTracker_Pruebas
rem   2) con SQLite en memoria
rem  Resultados (con el resultado obtenido de cada prueba) en
rem  docs\pruebas\resultados_*.xml y salida en scripts\logs\pruebas.log
rem ============================================================
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
set "LOG=%~dp0logs\pruebas.log"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
echo === Inicio: %DATE% %TIME% === > "%LOG%"
echo === 1. SQL Server (ScribeTracker_Pruebas) === >> "%LOG%"
set "ST_BD_PRUEBAS=ScribeTracker_Pruebas"
python -m pytest -v -p no:cacheprovider --junitxml="%~dp0..\docs\pruebas\resultados_windows_sqlserver.xml" >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo === 2. SQLite en memoria === >> "%LOG%"
set "ST_BD_PRUEBAS="
python -m pytest -v -p no:cacheprovider --junitxml="%~dp0..\docs\pruebas\resultados_windows_sqlite.xml" >> "%LOG%" 2>&1
echo === FIN: %DATE% %TIME% === >> "%LOG%"
endlocal
