@echo off
setlocal
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    set "JUVION_PYTHON=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "JUVION_PYTHON=.venv\Scripts\python.exe"
) else (
    echo Execute setup_writingway.bat primeiro para criar o ambiente Python 3.11.
    exit /b 1
)
"%JUVION_PYTHON%" package_app.py --install-dependencies
exit /b %errorlevel%
