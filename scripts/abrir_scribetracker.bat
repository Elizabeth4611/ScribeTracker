@echo off
rem ============================================================
rem  ABRIR SCRIBETRACKER (uso diario en esta laptop)
rem  Enciende todo lo que el sistema necesita y abre el navegador:
rem   1) SQL Server (pide permiso de administrador solo si esta apagado)
rem   2) Flask  -> http://127.0.0.1:5000
rem   3) Angular -> http://localhost:4200
rem  No cierres las ventanas "ScribeTracker - Flask" y "- Angular"
rem  mientras uses el sistema.
rem ============================================================
chcp 65001 >nul
echo 1/3 Revisando SQL Server...
sc query MSSQL$SQLEXPRESS02 | findstr /i "RUNNING" >nul
if errorlevel 1 (
  echo     SQL Server esta apagado. Acepta el permiso de administrador que aparece.
  powershell -NoProfile -Command "Start-Process -FilePath cmd -ArgumentList '/c net start MSSQL$SQLEXPRESS02' -Verb RunAs -Wait"
  sc query MSSQL$SQLEXPRESS02 | findstr /i "RUNNING" >nul
  if errorlevel 1 ( echo     No se pudo encender SQL Server. Ejecuta iniciar_sql.bat & pause & exit /b 1 )
)
echo     SQL Server listo.
echo 2/3 Encendiendo Flask y Angular...
call "%~dp0iniciar.bat" >nul
echo 3/3 Esperando a que Angular termine de compilar (puede tardar 1 minuto)...
for /l %%i in (1,1,90) do (
  netstat -aon | findstr ":4200 " | findstr LISTENING >nul && goto listo
  timeout /t 2 >nul
)
echo Angular tardo demasiado. Revisa la ventana "ScribeTracker - Angular".
pause
exit /b 1
:listo
timeout /t 3 >nul
start "" "http://localhost:4200"
echo Listo. ScribeTracker esta abierto en el navegador.
timeout /t 5 >nul
