# Visual Regression Scanner - Startskript
# Verwendung: .\run.ps1 SITEMAP_URL [OPTIONS]
#
# Nutzt die virtuelle Umgebung (.venv) falls vorhanden,
# sonst das globale Python.

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    & $venvPython -m visual_regression_scanner @args
} else {
    python -m visual_regression_scanner @args
}
