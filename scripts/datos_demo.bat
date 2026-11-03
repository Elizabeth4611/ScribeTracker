@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if not exist "%~dp0logs" mkdir "%~dp0logs"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
python "%~dp0datos_demo.py" > "%~dp0logs\datos_demo.log" 2>&1
echo === FIN === >> "%~dp0logs\datos_demo.log"
endlocal
