# Desbloquear todos los archivos descargados de internet y lanzar la app
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Get-ChildItem -Path $dir -Recurse | Unblock-File
Start-Process "$dir\pdf-foliado.exe"
