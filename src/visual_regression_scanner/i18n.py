"""Sprachwahl.

Vorerst nur die Erkennung der Startsprache - sie wird fuer den
Haftungshinweis beim Programmstart gebraucht. Die uebrige Oberflaeche ist noch
einsprachig; wenn sie auf Sprachdateien umgestellt wird, kommen `load_locale()`
und `t()` nach dem Muster der Schwester-Werkzeuge hier dazu.
"""

from __future__ import annotations

import contextlib
import locale
import os

SUPPORTED_LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "en"


def detect_language() -> str:
    """Leitet die Startsprache aus der Systemumgebung ab.

    Deutsch wird nur bei einer nachweislich deutschsprachigen Umgebung gewaehlt.
    Jeder andere Fall - unbekannte Sprache, leere Umgebung oder ein Fehler beim
    Auslesen (locale.getlocale() wirft auf manchen Systemen) - fuehrt zu
    Englisch, der Sprache der Projektdokumentation.

    Returns:
        "de" fuer eine deutschsprachige Umgebung, sonst immer "en".
    """
    code = ""
    with contextlib.suppress(Exception):
        code = locale.getlocale()[0] or ""
    if not code:
        with contextlib.suppress(Exception):
            code = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return "de" if code.lower().startswith("de") else "en"
