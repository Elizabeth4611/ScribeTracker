@echo off
rem ============================================================
rem  Etapa 2: dependencias, respaldo + migración de la base real,
rem  migración de una base de pruebas separada y pruebas.
rem  Salida completa en scripts\logs\etapa2_bd.log
rem ============================================================
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\etapa2_bd.log"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat

echo === 1. pip install (reportlab para PDF) === > "%LOG%"
python -m pip install -r requirements-dev.txt >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === 2. Respaldo y migración de la base REAL === >> "%LOG%"
python "%~dp0respaldar_y_migrar.py" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR EN LA MIGRACION: no se continua. >> "%LOG%"
  goto :fin
)

echo. >> "%LOG%"
echo === 3. Base de PRUEBAS separada (ScribeTracker_Pruebas) === >> "%LOG%"
set "ST_BD_PRUEBAS=ScribeTracker_Pruebas"
python "%~dp0crear_bd_pruebas.py" >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === 4. Pruebas automáticas contra SQL Server (base de pruebas) === >> "%LOG%"
python -m pytest -v -p no:cacheprovider --junitxml="%~dp0..\docs\pruebas\resultados_windows_sqlserver.xml" >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === 5. Pruebas automáticas con SQLite en memoria (Windows) === >> "%LOG%"
set "ST_BD_PRUEBAS="
python -m pytest -q -p no:cacheprovider --junitxml="%~dp0..\docs\pruebas\resultados_windows_sqlite.xml" >> "%LOG%" 2>&1

:fin
echo. >> "%LOG%"
echo === FIN === >> "%LOG%"
endlocal
