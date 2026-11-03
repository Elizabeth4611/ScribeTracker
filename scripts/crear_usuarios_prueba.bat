@echo off
rem Crea usuarios de prueba. Salida en scripts\logs\crear_usuarios.log
setlocal
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
python "%~dp0crear_usuarios_prueba.py" > "%LOGDIR%\crear_usuarios.log" 2>&1
echo === FIN === >> "%LOGDIR%\crear_usuarios.log"
endlocal
