"""Modal-Screen fuer Diff-Details."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static
from rich.text import Text

from ..models.scan_result import ComparisonStatus, ScreenshotResult


class DiffDetailScreen(ModalScreen):
    """Modal-Dialog mit ausfuehrlichen Diff-Details einer URL."""

    DEFAULT_CSS = """
    DiffDetailScreen {
        align: center middle;
    }

    DiffDetailScreen > Vertical {
        width: 80%;
        max-width: 100;
        height: 80%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    DiffDetailScreen #detail-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    DiffDetailScreen #detail-content {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    DiffDetailScreen #detail-footer {
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Schliessen"),
        Binding("q", "close", "Schliessen"),
    ]

    def __init__(self, result: ScreenshotResult, **kwargs) -> None:
        super().__init__(**kwargs)
        self._result = result

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        with Vertical():
            yield Static(f"Diff-Details: {self._result.url}", id="detail-title")
            yield Static(self._build_content(), id="detail-content")
            yield Static("ESC / q = Schliessen", id="detail-footer")

    def _build_content(self) -> Text:
        """Erstellt den Detail-Text.

        Returns:
            Formatierter Rich Text mit allen Diff-Details.
        """
        result = self._result
        text = Text()

        text.append(f"URL: {result.url}\n", style="bold")
        text.append(f"HTTP Status: {result.http_status_code}\n")
        text.append(f"Ladezeit: {result.load_time_ms}ms\n")
        text.append(f"Retries: {result.retry_count}\n\n")

        # Status
        text.append("Status: ", style="bold")
        status_style = {
            ComparisonStatus.MATCH: "bold green",
            ComparisonStatus.DIFF: "bold red",
            ComparisonStatus.NEW_BASELINE: "bold blue",
            ComparisonStatus.ERROR: "bold red",
            ComparisonStatus.TIMEOUT: "bold yellow",
        }.get(result.status, "")
        text.append(f"{result.status_icon}\n\n", style=status_style)

        if result.status == ComparisonStatus.NEW_BASELINE:
            text.append("Neue Baseline - kein Vergleich moeglich.\n", style="blue")
            if result.screenshot_path:
                text.append(f"Screenshot: {result.screenshot_path}\n", style="dim")
            return text

        if result.status in (ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT):
            text.append(f"Fehler: {result.error_message}\n", style="red")
            return text

        # Diff-Details
        text.append(f"Diff: {result.diff_percentage:.4f}%\n", style="bold")
        text.append(f"Geaenderte Pixel: {result.diff_pixel_count:,}\n")
        text.append(f"Gesamt Pixel: {result.total_pixel_count:,}\n")
        text.append(f"Threshold: {result.threshold}%\n\n")

        if result.baseline_path:
            text.append(f"Baseline: {result.baseline_path}\n", style="dim")
        if result.screenshot_path:
            text.append(f"Screenshot: {result.screenshot_path}\n", style="dim")
        if result.diff_path:
            text.append(f"Diff-Bild: {result.diff_path}\n", style="dim")

        return text

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
