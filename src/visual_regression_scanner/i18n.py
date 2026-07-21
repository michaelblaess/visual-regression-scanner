"""i18n - Internationalisierung ueber JSON-Sprachdateien.

Aufbau wie in den Schwester-Werkzeugen (c2pa-scanner, sitemap-tracker,
console-error-scanner): je Sprache eine flache JSON-Datei unter ``locale/``,
Zugriff ueber ``t()``.

Die Ausweichsprache ist Englisch: Das Projekt ist englischsprachig
dokumentiert, und ein Text in einer Sprache, die der Nutzer nicht liest, hilft
niemandem.
"""

from __future__ import annotations

import contextlib
import json
import locale
import logging
import os
from importlib import resources

logger = logging.getLogger(__name__)

_strings: dict[str, str] = {}
_current_lang: str = "en"

SUPPORTED_LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "en"


def detect_language() -> str:
    """Leitet die Startsprache aus der Systemumgebung ab.

    Nur beim allerersten Start relevant - danach steht die Sprache in den
    Einstellungen. Deutsch wird nur bei einer nachweislich deutschsprachigen
    Umgebung gewaehlt. Jeder andere Fall - unbekannte Sprache, leere Umgebung
    oder ein Fehler beim Auslesen (locale.getlocale() wirft auf manchen
    Systemen) - fuehrt zu Englisch.

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


def load_locale(lang: str) -> None:
    """Laedt eine Sprachdatei (z.B. 'de', 'en').

    Args:
        lang:
        Sprachkuerzel. Unbekannte Werte fallen auf Englisch zurueck.
    """
    global _strings, _current_lang

    if lang not in SUPPORTED_LANGUAGES:
        logger.warning("Sprache '%s' nicht unterstuetzt, verwende '%s'", lang, DEFAULT_LANGUAGE)
        lang = DEFAULT_LANGUAGE

    try:
        locale_file = resources.files("visual_regression_scanner") / "locale" / f"{lang}.json"
        _strings = json.loads(locale_file.read_text(encoding="utf-8"))
        _current_lang = lang
    except Exception:
        logger.exception("Fehler beim Laden der Sprachdatei '%s'", lang)
        _strings = {}
        _current_lang = lang


def current_language() -> str:
    """Gibt die aktuell geladene Sprache zurueck."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Uebersetzt einen Schluessel. Platzhalter via {name} und kwargs.

    Fehlt der Schluessel, wird er selbst zurueckgegeben - so faellt eine Luecke
    in der Oberflaeche auf, statt einen leeren Text zu erzeugen.
    """
    template = _strings.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
