@echo off
rem Ejecuta los casos del reporte de pruebas contra SQL Server (base de pruebas)
rem y guarda la salida de cada uno en docs\evidencias\salidas\
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
python "%~dp0evidencias\ejecutar_casos.py" > "%~dp0logs\evidencias_sqlserver.log" 2>&1
echo === FIN === >> "%~dp0logs\evidencias_sqlserver.log"
endlocal
