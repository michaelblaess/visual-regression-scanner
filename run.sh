#!/usr/bin/env bash
# Visual Regression Scanner - Startskript
# Verwendung: ./run.sh SITEMAP_URL [OPTIONS]
#
# Nutzt die virtuelle Umgebung (.venv) falls vorhanden,
# sonst das globale Python.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ -f "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" -m visual_regression_scanner "$@"
else
    python3 -m visual_regression_scanner "$@"
fi
