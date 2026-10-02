@echo off
setlocal
cd /d "%~dp0"
set KMP_DUPLICATE_LIB_OK=TRUE
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    echo Ambiente do Juvion ausente. Execute setup_writingway.bat primeiro.
    pause
    exit /b 1
)
if errorlevel 1 pause
