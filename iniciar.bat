@echo off
cd /d "%~dp0"

echo Verificando Python...
py --version 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Python no encontrado.
    echo Instala Python 3.11 o 3.12 desde: https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" al instalar.
    pause
    exit /b 1
)

echo Instalando dependencias...
py -m pip install -r requirements.txt ^
    --trusted-host pypi.org ^
    --trusted-host files.pythonhosted.org ^
    --trusted-host pypi.python.org ^
    -q

if errorlevel 1 (
    echo.
    echo ERROR: Fallo la instalacion de dependencias.
    echo Si estas en una red corporativa, pide a TI que permita acceso a pypi.org
    pause
    exit /b 1
)

set PYTHONPATH=%~dp0
py pdf_foliado/main.py

if errorlevel 1 (
    echo.
    echo ERROR: La aplicacion cerro con un error. Revisa el mensaje arriba.
    pause
)
