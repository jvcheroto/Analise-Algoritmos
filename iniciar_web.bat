@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Crie o ambiente primeiro: py -m venv .venv
    exit /b 1
)
".venv\Scripts\python.exe" iniciar_web.py %*
