@echo off
chcp 936 >nul
set PYTHONDONTWRITEBYTECODE=1

pythonw main.py --gui
