# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for pdf-foliado.exe — portable, no install, no console."""

excludes = [
    "unittest", "doctest", "email", "html", "http", "xmlrpc", "xml",
    "ftplib", "imaplib", "smtplib", "poplib", "telnetlib", "nntplib",
    "PySide6.QtWebEngine", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork", "PySide6.Qt3D", "PySide6.Qt3DCore",
    "PySide6.QtBluetooth", "PySide6.QtWebSockets",
    "PySide6.QtDataVisualization", "PySide6.QtCharts",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtTest", "PySide6.QtSql",
    "PySide6.QtLocation", "PySide6.QtPositioning", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtTextToSpeech", "PySide6.QtVirtualKeyboard",
    "tkinter", "curses", "readline", "pty", "termios",
    "matplotlib", "numpy", "scipy", "pandas",
    "IPython", "notebook", "jupyter",
]

a = Analysis(
    ["../pdf_foliado/main.py"],
    pathex=[".."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "pikepdf._core",
        "reportlab.pdfbase._fontdata_enc_winansi",
        "reportlab.pdfbase._fontdata_enc_macroman",
        "reportlab.pdfbase._fontdata_enc_macexpert",
        "reportlab.pdfbase._fontdata_enc_standard",
        "reportlab.pdfbase._fontdata_enc_symbol",
        "reportlab.pdfbase._fontdata_enc_zapfdingbats",
    ],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdf-foliado",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="pdf-foliado",
)
