@echo off
rem ============================================================
rem  Prepara la base de datos de ScribeTracker en Azure SQL:
rem  crea las tablas y (si dices que si) copia los datos de tu
rem  base local. Te pide la contrasena de SQL de Azure; no se guarda.
rem ============================================================
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
title ScribeTracker - base de datos en Azure
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
python "%~dp0azure_bd.py"
echo.
pause
endlocal
