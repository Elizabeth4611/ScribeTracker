@echo off
rem Instala pytest, corre las pruebas y revisa la conexion a SQL Server.
rem La salida queda en scripts\logs\backend.log
setlocal
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\backend.log"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat

echo === pip install -r requirements-dev.txt === > "%LOG%"
python -m pip install -r requirements-dev.txt >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === pytest === >> "%LOG%"
python -m pytest -q >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === comandos de flask === >> "%LOG%"
flask --app app --help >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === rutas de flask === >> "%LOG%"
flask --app app routes >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === usuarios en SQL Server por rol y estatus (sin datos personales) === >> "%LOG%"
python -c "from app import create_app; from app.extensions import db; from app.models import Usuario; from sqlalchemy import func; a = create_app(); c = a.app_context(); c.push(); print(db.session.execute(db.select(Usuario.rol, Usuario.estatus, func.count()).group_by(Usuario.rol, Usuario.estatus)).all())" >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === FIN === >> "%LOG%"
echo Listo. Revisa scripts\logs\backend.log
endlocal
