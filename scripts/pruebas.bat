@echo off
rem Corre las pruebas automaticas del backend (pytest) con una base SQLite
rem en memoria: no toca la base real. Resultado en scripts\logs\pruebas.log
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
set "LOG=%~dp0logs\pruebas.log"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
set "ST_BD_PRUEBAS="
python -m pytest -v -p no:cacheprovider > "%LOG%" 2>&1
type "%LOG%" | findstr /r /c:"passed" /c:"failed"
echo Detalle en scripts\logs\pruebas.log
pause
endlocal
