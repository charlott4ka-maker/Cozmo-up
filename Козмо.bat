@echo off
rem Запуск приложения Козмо двойным щелчком.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" app.py
) else (
    echo Окружение не найдено. Сначала выполните установку:
    echo   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
    pause
)
