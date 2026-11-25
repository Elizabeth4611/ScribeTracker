@echo off
rem Crea el primer usuario Administrador. Pide nombre, correo y contrasena
rem (minimo 8 caracteres). La contrasena no se guarda en ningun archivo.
setlocal
chcp 65001 >nul
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
flask --app app create-admin
pause
endlocal
