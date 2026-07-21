"""Persistente Einstellungen fuer den Visual Regression Scanner.

Die Werte liegen als JSON im Benutzerverzeichnis, neben der Zustimmung zum
Haftungshinweis. Angaben auf der Kommandozeile haben Vorrang: sie gelten fuer
den laufenden Aufruf, ohne die gespeicherten Werte zu ueberschreiben.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import detect_language

logger = logging.getLogger(__name__)

SETTINGS_DIR = Path.home() / ".visual-regression-scanner"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class Settings:
    """Gespeicherte Voreinstellungen.

    Attributes:
        theme:
            Name des Textual-Themes.
        language:
            Sprachkuerzel der Oberflaeche; beim Erststart aus der Umgebung.
        threshold:
            Schwelle in Prozent, ab der ein Unterschied als Abweichung gilt.
        viewport:
            Fenstergroesse fuer die Aufnahme als "BreitexHoehe".
        full_page:
            Ganze Seite aufnehmen statt nur des sichtbaren Bereichs.
        concurrency:
            Gleichzeitig geoeffnete Browser-Tabs.
        rate_limit_enabled:
            Ob die Aufrufe gedrosselt werden.
        rate_per_minute:
            Hoechstzahl der Seiten pro Minute, wenn gedrosselt wird.
        timeout:
            Zeitgrenze je Seite in Sekunden.
        respect_robots:
            Gesperrte Seiten aus der Sitemap ueberspringen.
        no_headless:
            Browser sichtbar starten (zur Fehlersuche).
        user_agent:
            Abweichende Kennung; leer = eingebauter Chrome-Wert.
        cookies:
            Rohform "name=wert, name2=wert2".
        proxy_url:
            Optionaler Unternehmens-Proxy fuer httpx und den Browser.
    """

    theme: str = "textual-dark"
    language: str = field(default_factory=detect_language)
    threshold: float = 0.1
    viewport: str = "1920x1080"
    full_page: bool = True
    concurrency: int = 4
    # Voreingestellt gedrosselt: fuer jeden Screenshot wird die Seite
    # vollstaendig gerendert und wiegt damit ein Vielfaches eines Abrufs.
    rate_limit_enabled: bool = True
    rate_per_minute: int = 60
    timeout: int = 30
    respect_robots: bool = True
    no_headless: bool = False
    # Grafische Vorschau (Sixel/TGP) ist opt-in: auf manchen Terminals
    # stoert ein Bild-Widget die uebrige Darstellung.
    graphics_preview: bool = False
    user_agent: str = ""
    cookies: str = ""
    proxy_url: str = ""

    def to_dict(self) -> dict[str, object]:
        """Wandelt die Einstellungen in ein Dictionary fuer die JSON-Datei."""
        return {
            "theme": self.theme,
            "language": self.language,
            "threshold": self.threshold,
            "viewport": self.viewport,
            "full_page": self.full_page,
            "concurrency": self.concurrency,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_per_minute": self.rate_per_minute,
            "timeout": self.timeout,
            "respect_robots": self.respect_robots,
            "no_headless": self.no_headless,
            "graphics_preview": self.graphics_preview,
            "user_agent": self.user_agent,
            "cookies": self.cookies,
            "proxy_url": self.proxy_url,
        }

    def save(self) -> None:
        """Schreibt die Einstellungen in die JSON-Datei."""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls) -> Settings:
        """Laedt die Einstellungen; fehlende oder kaputte Datei ergibt Vorgabewerte.

        Returns:
            Settings-Instanz.
        """
        settings = cls()
        if not SETTINGS_FILE.is_file():
            return settings

        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("Einstellungen nicht lesbar, verwende Vorgabewerte")
            return settings
        if not isinstance(data, dict):
            return settings

        settings.theme = str(data.get("theme", settings.theme))
        settings.language = str(data.get("language", settings.language))
        settings.viewport = str(data.get("viewport", settings.viewport))
        settings.user_agent = str(data.get("user_agent", settings.user_agent))
        settings.cookies = str(data.get("cookies", settings.cookies))
        settings.proxy_url = str(data.get("proxy_url", settings.proxy_url))
        settings.full_page = bool(data.get("full_page", settings.full_page))
        settings.rate_limit_enabled = bool(data.get("rate_limit_enabled", settings.rate_limit_enabled))
        settings.respect_robots = bool(data.get("respect_robots", settings.respect_robots))
        settings.no_headless = bool(data.get("no_headless", settings.no_headless))
        settings.graphics_preview = bool(data.get("graphics_preview", settings.graphics_preview))
        # Zahlenwerte einzeln absichern: eine von Hand verstellte Datei darf
        # den Start nicht verhindern.
        with contextlib.suppress(TypeError, ValueError):
            settings.threshold = float(data.get("threshold", settings.threshold))
        with contextlib.suppress(TypeError, ValueError):
            settings.concurrency = int(data.get("concurrency", settings.concurrency))
        with contextlib.suppress(TypeError, ValueError):
            settings.rate_per_minute = int(data.get("rate_per_minute", settings.rate_per_minute))
        with contextlib.suppress(TypeError, ValueError):
            settings.timeout = int(data.get("timeout", settings.timeout))
        return settings


def parse_cookies(raw: str) -> list[dict[str, str]]:
    """Zerlegt einen Cookie-String in eine Liste von Cookie-Dicts.

    Format: ``name=wert, name2=wert2`` (kommagetrennt). Eintraege ohne ``=``
    werden uebergangen.

    Args:
        raw:
            Rohform, wie sie in den Einstellungen steht.

    Returns:
        Liste aus Dicts mit den Schluesseln ``name`` und ``value``.
    """
    cookies: list[dict[str, str]] = []
    for part in raw.split(","):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        if name.strip():
            cookies.append({"name": name.strip(), "value": value.strip()})
    return cookies
