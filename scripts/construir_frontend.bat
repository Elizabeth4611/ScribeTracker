@echo off
rem Instala las dependencias de Angular y compila el frontend.
rem La salida queda en scripts\logs\frontend.log
setlocal
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\frontend.log"
cd /d "%~dp0..\frontend"

echo === node y npm === > "%LOG%"
node --version >> "%LOG%" 2>&1
call npm --version >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === npm install === >> "%LOG%"
call npm install --no-fund --no-audit >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === npm run build === >> "%LOG%"
call npm run build >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo === FIN === >> "%LOG%"
echo Listo. Revisa scripts\logs\frontend.log
endlocal
