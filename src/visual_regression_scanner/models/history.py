"""Verlauf der geprueften Sitemaps.

Haelt fest, welche Sitemap mit welchen Einstellungen geprueft wurde und was
dabei herauskam. Beim erneuten Aufruf laesst sich ein Eintrag auswaehlen,
statt die URL noch einmal einzutippen.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_DIR = Path.home() / ".visual-regression-scanner"
HISTORY_FILE = HISTORY_DIR / "history.json"

# Aeltere Eintraege werden verworfen - der Verlauf soll eine Auswahlhilfe
# bleiben und keine Datensammlung werden.
MAX_ENTRIES = 30


@dataclass
class HistoryEntry:
    """Ein geprueftes Ziel samt Einstellungen und Ergebnis.

    Attributes:
        url:
            Sitemap-URL oder Pfad zur lokalen Datei.
        timestamp:
            Zeitpunkt im ISO-Format.
        viewport:
            Verwendete Fenstergroesse als "BreitexHoehe".
        threshold:
            Verwendete Diff-Schwelle in Prozent.
        full_page:
            Ob die ganze Seite aufgenommen wurde.
        total_pages:
            Anzahl gepruefter Seiten.
        total_changed:
            Anzahl Seiten mit Abweichung.
        total_failed:
            Anzahl fehlgeschlagener Seiten.
    """

    url: str
    timestamp: str = ""
    viewport: str = ""
    threshold: float = 0.1
    full_page: bool = True
    total_pages: int = 0
    total_changed: int = 0
    total_failed: int = 0

    def to_dict(self) -> dict[str, object]:
        """Wandelt den Eintrag in ein Dictionary fuer die JSON-Datei."""
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "viewport": self.viewport,
            "threshold": self.threshold,
            "full_page": self.full_page,
            "total_pages": self.total_pages,
            "total_changed": self.total_changed,
            "total_failed": self.total_failed,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> HistoryEntry:
        """Baut einen Eintrag aus einem Dictionary.

        Unbekannte oder kaputte Werte fallen auf die Vorgabe zurueck, damit ein
        von Hand bearbeiteter Verlauf den Start nicht verhindert.
        """
        entry = HistoryEntry(url=str(data.get("url", "")))
        entry.timestamp = str(data.get("timestamp", ""))
        entry.viewport = str(data.get("viewport", ""))
        entry.full_page = bool(data.get("full_page", True))
        try:
            entry.threshold = float(str(data.get("threshold", 0.1)))
        except (TypeError, ValueError):
            entry.threshold = 0.1
        for name in ("total_pages", "total_changed", "total_failed"):
            try:
                setattr(entry, name, int(str(data.get(name, 0))))
            except (TypeError, ValueError):
                setattr(entry, name, 0)
        return entry

    @property
    def display_time(self) -> str:
        """Zeitpunkt in deutscher Schreibweise, oder "?" wenn unbekannt."""
        if not self.timestamp:
            return "?"
        try:
            return datetime.fromisoformat(self.timestamp).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return self.timestamp[:16].replace("T", " ")

    @property
    def display_result(self) -> str:
        """Kurzfassung des Ergebnisses fuer die Auswahlliste."""
        if not self.total_pages:
            return "-"
        parts = [f"{self.total_pages} Seiten"]
        if self.total_changed:
            parts.append(f"{self.total_changed} geändert")
        if self.total_failed:
            parts.append(f"{self.total_failed} Fehler")
        return ", ".join(parts)


@dataclass
class History:
    """Zugriff auf den gespeicherten Verlauf."""

    entries: list[HistoryEntry] = field(default_factory=list)

    @staticmethod
    def load() -> list[HistoryEntry]:
        """Laedt den Verlauf; eine fehlende oder kaputte Datei ergibt eine leere Liste."""
        if not HISTORY_FILE.is_file():
            return []
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.exception("Verlauf nicht lesbar")
            return []
        if not isinstance(data, list):
            return []
        return [HistoryEntry.from_dict(item) for item in data if isinstance(item, dict)]

    @staticmethod
    def save(entries: list[HistoryEntry]) -> None:
        """Schreibt den Verlauf, gekuerzt auf die juengsten Eintraege."""
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        payload = [entry.to_dict() for entry in entries[:MAX_ENTRIES]]
        HISTORY_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def add(entry: HistoryEntry) -> None:
        """Stellt einen Eintrag nach vorne und entfernt aeltere zur selben URL.

        Ohne das Entfernen wuerde derselbe wiederholt gepruefte Auftritt die
        Liste fuellen und aeltere, andere Ziele verdraengen.
        """
        if not entry.timestamp:
            entry.timestamp = datetime.now().isoformat(timespec="seconds")  # noqa: DTZ005
        entries = [item for item in History.load() if item.url != entry.url]
        entries.insert(0, entry)
        History.save(entries)

    @staticmethod
    def update_latest_stats(url: str, pages: int, changed: int, failed: int) -> None:
        """Traegt das Ergebnis in den juengsten Eintrag zur URL nach.

        Der Eintrag entsteht beim Laden der Sitemap - die Zahlen stehen aber
        erst fest, wenn der Durchlauf fertig ist.
        """
        entries = History.load()
        for entry in entries:
            if entry.url == url:
                entry.total_pages = pages
                entry.total_changed = changed
                entry.total_failed = failed
                History.save(entries)
                return
