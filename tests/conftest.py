"""Gemeinsame Test-Vorbereitung.

Alle Tests laufen gegen eine temporaere Einstellungsdatei. Ohne diese Trennung
wuerden sie die echten Einstellungen des Benutzers lesen - und damit von
Werten abhaengen, die sich jederzeit aendern koennen. Ein Test, der heute gruen
ist und morgen rot, weil jemand einen Regler verschoben hat, ist wertlos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from visual_regression_scanner.models import settings as settings_module


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Legt Einstellungen und Zustimmung in ein temporaeres Verzeichnis."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", path)
    return path
