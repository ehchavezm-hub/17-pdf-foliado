@echo off
cd /d "%~dp0"
py pdf_foliado/main.py
if errorlevel 1 (
    echo.
    echo Error al iniciar.
    echo Instala las dependencias primero con:
    echo   pip install -r requirements.txt
    pause
)
