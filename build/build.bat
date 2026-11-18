@echo off
setlocal

echo === pdf-foliado build ===
cd /d "%~dp0"

pip install pyinstaller --quiet

echo [1/3] Running PyInstaller...
pyinstaller --clean pdf-foliado.spec
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

echo [2/3] Creating ZIP...
cd dist
powershell -NoProfile -Command "Compress-Archive -Path pdf-foliado -DestinationPath pdf-foliado.zip -Force"
if errorlevel 1 (
    echo ERROR: ZIP creation failed.
    exit /b 1
)

echo [3/3] ZIP size:
powershell -NoProfile -Command "(Get-Item pdf-foliado.zip).length / 1MB | Write-Host -NoNewline; Write-Host ' MB'"

echo.
echo === Build complete: dist\pdf-foliado.zip ===
endlocal
