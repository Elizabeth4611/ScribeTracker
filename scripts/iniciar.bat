@echo off
rem Detiene instancias anteriores (puertos 5000 y 4200) y abre dos ventanas:
rem Flask (http://127.0.0.1:5000) y Angular (http://localhost:4200).
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":5000 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":4200 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1
start "ScribeTracker - Flask" /D "%~dp0..\backend" cmd /k ".venv\Scripts\activate.bat && flask --app app run"
start "ScribeTracker - Angular" /D "%~dp0..\frontend" cmd /k "npm start"
echo Cuando Angular termine de compilar, abre http://localhost:4200
