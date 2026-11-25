@echo off
rem Inicia el servicio de SQL Server (instancia SQLEXPRESS02). Pide permiso de administrador.
net session >nul 2>&1 || (powershell -NoProfile -Command "Start-Process -FilePath %~f0 -Verb RunAs" & exit /b)
net start MSSQL$SQLEXPRESS02
sc query MSSQL$SQLEXPRESS02 | findstr /i "ESTADO STATE"
echo.
echo Si dice RUNNING o "ya se ha iniciado", SQL Server esta listo. Puedes cerrar esta ventana.
pause
