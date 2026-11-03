@echo off
rem Evidencias con SQL Server (base de pruebas ScribeTracker_Pruebas):
rem resultados HTTP de los casos, capturas de la interfaz Angular y caso F08.
rem No toca la base real. Resultado en scripts\logs\sqlserver_interfaz.log
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "LOG=%~dp0logs\sqlserver_interfaz.log"
if not exist "%~dp0logs" mkdir "%~dp0logs"
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
echo === Inicio %DATE% %TIME% === > "%LOG%"
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
  echo === Instalando Playwright para Python ^(solo la primera vez^) === >> "%LOG%"
  python -m pip install playwright==1.55.0 >> "%LOG%" 2>&1
)
echo === Navegador Chromium de Playwright === >> "%LOG%"
python -m playwright install chromium >> "%LOG%" 2>&1
python "%~dp0evidencias\ejecutar_sqlserver_interfaz.py" >> "%LOG%" 2>&1
echo Codigo de salida: %ERRORLEVEL% >> "%LOG%"
echo === FIN %DATE% %TIME% === >> "%LOG%"
endlocal
