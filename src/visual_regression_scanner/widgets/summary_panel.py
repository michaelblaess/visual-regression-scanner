"""Summary-Widget mit Zaehler und Uebersicht."""

from __future__ import annotations

from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget

from ..models.scan_result import ComparisonStatus, ScreenshotResult


class SummaryPanel(Widget):
    """Zeigt eine Zusammenfassung des Vergleichs-Fortschritts."""

    DEFAULT_CSS = """
    SummaryPanel {
        height: auto;
        min-height: 3;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sitemap_url: str = ""
        self._total_urls: int = 0
        self._scanned: int = 0
        self._matches: int = 0
        self._diffs: int = 0
        self._new_baselines: int = 0
        self._errors: int = 0
        self._timeouts: int = 0

    def render(self) -> RenderResult:
        """Rendert die Zusammenfassung."""
        text = Text()

        if not self._sitemap_url:
            return Text("Keine Sitemap geladen.", style="dim italic")

        # Zeile 1: Sitemap + Fortschritt
        text.append(" Sitemap: ", style="bold")
        text.append(self._sitemap_url, style="dim")
        text.append("  |  ", style="dim")
        text.append(f"{self._total_urls} URLs", style="bold")

        if self._scanned > 0:
            text.append(f"  ({self._scanned}/{self._total_urls} gescannt)", style="dim")

        # Zeile 2: Vergleichs-Zaehler
        text.append("\n")

        if self._scanned > 0:
            if self._diffs > 0:
                text.append(f" {self._diffs} Diffs", style="bold red")
            else:
                text.append(" Keine Diffs", style="bold green")

            text.append("  |  ")
            text.append(f"OK: {self._matches}", style="bold green" if self._matches > 0 else "dim")
            text.append("  |  ")
            text.append(f"Neu: {self._new_baselines}", style="bold blue" if self._new_baselines > 0 else "dim")
            text.append("  |  ")
            text.append(f"Fehler: {self._errors}", style="bold red" if self._errors > 0 else "dim")
            text.append("  |  ")
            text.append(f"Timeout: {self._timeouts}", style="bold yellow" if self._timeouts > 0 else "dim")

        return text

    def set_sitemap(self, sitemap_url: str, url_count: int) -> None:
        """Setzt Sitemap-Info ohne Scan-Ergebnisse.

        Args:
            sitemap_url: URL der Sitemap.
            url_count: Anzahl der URLs in der Sitemap.
        """
        self._sitemap_url = sitemap_url
        self._total_urls = url_count
        self._scanned = 0
        self._matches = 0
        self._diffs = 0
        self._new_baselines = 0
        self._errors = 0
        self._timeouts = 0
        self.refresh()

    def update_from_results(self, results: list[ScreenshotResult]) -> None:
        """Aktualisiert die Zusammenfassung aus den Vergleichs-Ergebnissen.

        Args:
            results: Liste der aktuellen Vergleichs-Ergebnisse.
        """
        self._scanned = 0
        self._matches = 0
        self._diffs = 0
        self._new_baselines = 0
        self._errors = 0
        self._timeouts = 0

        for r in results:
            if r.status == ComparisonStatus.MATCH:
                self._scanned += 1
                self._matches += 1
            elif r.status == ComparisonStatus.DIFF:
                self._scanned += 1
                self._diffs += 1
            elif r.status == ComparisonStatus.NEW_BASELINE:
                self._scanned += 1
                self._new_baselines += 1
            elif r.status == ComparisonStatus.ERROR:
                self._scanned += 1
                self._errors += 1
            elif r.status == ComparisonStatus.TIMEOUT:
                self._scanned += 1
                self._timeouts += 1

        self.refresh()
