@echo off
cd /d "%~dp0"
pip install -r requirements.txt -q
set PYTHONPATH=%~dp0
py pdf_foliado/main.py
