"""Tests fuer die Sprachdateien.

Die Oberflaeche liegt vollstaendig in ``locale/de.json`` und ``locale/en.json``.
Diese Tests halten beide Dateien deckungsgleich und pruefen, dass kein Text im
Code auf einen Schluessel zeigt, den es nicht gibt - sonst stuende in der
Oberflaeche der Schluessel selbst.
"""

from __future__ import annotations

import json
import re
import string
from pathlib import Path

import pytest

from visual_regression_scanner import i18n

SRC = Path(__file__).resolve().parents[1] / "src" / "visual_regression_scanner"
LOCALE_DIR = SRC / "locale"

# Schluessel im Code: t("key") und Zeichenketten, die als Schluessel
# weitergereicht werden (Beschriftungen der Tastenkuerzel, Variablen).
_T_CALL = re.compile(r"""\bt\(\s*["']([a-z][a-z_0-9.]*)["']""")
_KEY_LITERAL = re.compile(r"""["']([a-z][a-z_0-9]*(?:\.[a-z_0-9]+)+)["']""")


def _load(lang: str) -> dict[str, str]:
    return json.loads((LOCALE_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _placeholders(template: str) -> set[str]:
    """Liefert die Namen der Platzhalter einer Vorlage."""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_beide_sprachen_haben_die_gleichen_schluessel() -> None:
    de, en = _load("de"), _load("en")
    assert set(de) == set(en)


def test_kein_leerer_text() -> None:
    for lang in i18n.SUPPORTED_LANGUAGES:
        for key, value in _load(lang).items():
            assert value.strip() or key == "table.col.index", f"{lang}: {key} ist leer"


def test_platzhalter_stimmen_zwischen_den_sprachen_ueberein() -> None:
    de, en = _load("de"), _load("en")
    for key in de:
        assert _placeholders(de[key]) == _placeholders(en[key]), key


def test_jeder_verwendete_schluessel_ist_uebersetzt() -> None:
    keys = set(_load("de"))
    fehlend: set[str] = set()
    for path in _source_files():
        for match in _T_CALL.finditer(path.read_text(encoding="utf-8")):
            if match.group(1) not in keys:
                fehlend.add(f"{path.name}: {match.group(1)}")
    assert not fehlend


def test_keine_unbenutzten_schluessel() -> None:
    """Ein Schluessel ohne Fundstelle im Code ist Ballast - oder ein Tippfehler."""
    verwendet: set[str] = set()
    for path in _source_files():
        verwendet.update(_KEY_LITERAL.findall(path.read_text(encoding="utf-8")))
    unbenutzt = set(_load("de")) - verwendet
    assert not unbenutzt, sorted(unbenutzt)


def test_unbekannter_schluessel_bleibt_sichtbar() -> None:
    i18n.load_locale("de")
    assert i18n.t("gibt.es.nicht") == "gibt.es.nicht"


def test_platzhalter_werden_gefuellt() -> None:
    i18n.load_locale("de")
    assert "42" in i18n.t("summary.urls", count=42)


@pytest.mark.parametrize("lang", i18n.SUPPORTED_LANGUAGES)
def test_sprache_laesst_sich_laden(lang: str) -> None:
    i18n.load_locale(lang)
    assert i18n.current_language() == lang
    assert i18n.t("binding.quit") != "binding.quit"


def test_unbekannte_sprache_faellt_auf_englisch_zurueck() -> None:
    i18n.load_locale("kl")
    assert i18n.current_language() == i18n.DEFAULT_LANGUAGE
