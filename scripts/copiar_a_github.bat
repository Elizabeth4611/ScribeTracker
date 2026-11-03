@echo off
rem Copia el trabajo de C:\ScribeTracker a la copia vinculada a GitHub, SIN
rem secretos: excluye .env, respaldos, logs (contraseñas de prueba), entornos
rem virtuales, node_modules y compilados. No borra nada en el destino, no hace
rem commit ni push. Al final revisa que no haya secretos.
setlocal
chcp 65001 >nul
set "ORIGEN=%~dp0.."
set "DESTINO=%USERPROFILE%\Documents\GitHub\ScribeTracker"
set "LOG=%~dp0logs\copiar_a_github.log"
if not exist "%~dp0logs" mkdir "%~dp0logs"
if not exist "%DESTINO%\.git" (
  echo No existe %DESTINO%\.git >> "%LOG%"
  echo No se encontro la copia de GitHub en %DESTINO%
  pause
  exit /b 1
)
robocopy "%ORIGEN%" "%DESTINO%" /E /NP /NFL /NDL ^
  /XD .git .venv node_modules dist .angular logs instance __pycache__ .pytest_cache *_respaldo ^
  /XF .env *.env *.bak *.pem *.key > "%LOG%" 2>&1
echo. >> "%LOG%"
echo === Revision de secretos === >> "%LOG%"
"%ORIGEN%\backend\.venv\Scripts\python.exe" "%~dp0revisar_antes_de_subir.py" "%DESTINO%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo NO SUBAS NADA: la revision encontro problemas. Mira scripts\logs\copiar_a_github.log
) else (
  echo Copia lista y revisada. Ahora abre GitHub Desktop. Detalle en scripts\logs\copiar_a_github.log
)
pause
endlocal
