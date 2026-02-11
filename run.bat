@echo off
REM Visual Regression Scanner - Startskript
REM Verwendung: run.bat SITEMAP_URL [OPTIONS]
REM
REM Nutzt die virtuelle Umgebung (.venv) falls vorhanden,
REM sonst das globale Python.

set VENV_PYTHON=%~dp0.venv\Scripts\python.exe

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m visual_regression_scanner %*
) else (
    python -m visual_regression_scanner %*
)
