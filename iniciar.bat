@echo off
cd /d "%~dp0"
pip install -r requirements.txt -q
py pdf_foliado/main.py
