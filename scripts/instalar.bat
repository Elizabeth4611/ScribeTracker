@echo off
rem ============================================================
rem  INSTALAR SCRIBETRACKER (solo la primera vez)
rem  Antes: crear la base vacia en SQL Server y el archivo backend\.env
rem  (ver README.md). Resultado en scripts\logs\instalar.log
rem ============================================================
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
set "LOG=%~dp0logs\instalar.log"
if not exist "%~dp0..\backend\.env" (
  echo Falta backend\.env. Copia backend\.env.example como backend\.env y llena sus datos.
  pause
  exit /b 1
)
cd /d "%~dp0..\backend"
echo 1/4 Creando el entorno de Python...
echo === 1. Entorno de Python === > "%LOG%"
if not exist ".venv\Scripts\activate.bat" python -m venv .venv >> "%LOG%" 2>&1
call .venv\Scripts\activate.bat
echo 2/4 Instalando dependencias de Python...
echo === 2. pip install === >> "%LOG%"
python -m pip install -r requirements-dev.txt >> "%LOG%" 2>&1
echo 3/4 Creando las tablas de la base de datos...
echo === 3. flask db upgrade === >> "%LOG%"
flask --app app db upgrade >> "%LOG%" 2>&1
if errorlevel 1 (
  echo ERROR al crear las tablas. Revisa scripts\logs\instalar.log y backend\.env
  pause
  exit /b 1
)
echo 4/4 Instalando y compilando Angular (puede tardar unos minutos)...
call "%~dp0construir_frontend.bat" >nul
echo.
echo Listo. Ahora ejecuta scripts\crear_admin.bat para crear el primer administrador.
echo Detalle en scripts\logs\instalar.log y scripts\logs\frontend.log
pause
endlocal
