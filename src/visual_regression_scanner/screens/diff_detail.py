"""Modal-Screen fuer Diff-Details."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ..i18n import t
from ..models.scan_result import ComparisonStatus, ScreenshotResult


class DiffDetailScreen(ModalScreen[None]):
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
        Binding("escape", "close", t("binding.close")),
        Binding("q", "close", t("binding.close")),
    ]

    def __init__(self, result: ScreenshotResult, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._result = result

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        with Vertical():
            yield Static(t("diffscreen.title", url=self._result.url), id="detail-title")
            yield Static(self._build_content(), id="detail-content")
            yield Static(t("diffscreen.footer"), id="detail-footer")

    def _build_content(self) -> Text:
        """Erstellt den Detail-Text.

        Returns:
            Formatierter Rich Text mit allen Diff-Details.
        """
        result = self._result
        text = Text()

        text.append(t("diffscreen.url", url=result.url), style="bold")
        text.append(t("diffscreen.http", code=result.http_status_code))
        text.append(t("diffscreen.load_time", ms=result.load_time_ms))
        text.append(t("diffscreen.retries", count=result.retry_count))

        # Status
        text.append(t("diffscreen.status"), style="bold")
        status_style = {
            ComparisonStatus.MATCH: "bold green",
            ComparisonStatus.DIFF: "bold red",
            ComparisonStatus.NEW_BASELINE: "bold blue",
            ComparisonStatus.ERROR: "bold red",
            ComparisonStatus.TIMEOUT: "bold yellow",
        }.get(result.status, "")
        text.append(f"{result.status_icon}\n\n", style=status_style)

        if result.status == ComparisonStatus.NEW_BASELINE:
            text.append(t("diffscreen.new_baseline"), style="blue")
            if result.screenshot_path:
                text.append(t("diffscreen.screenshot", path=result.screenshot_path), style="dim")
            return text

        if result.status in (ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT):
            text.append(t("diffscreen.error", error=result.error_message), style="red")
            return text

        # Diff-Details
        text.append(t("diffscreen.diff", pct=result.diff_percentage), style="bold")
        text.append(t("diffscreen.changed_pixels", count=result.diff_pixel_count))
        text.append(t("diffscreen.total_pixels", count=result.total_pixel_count))
        text.append(t("diffscreen.threshold", value=result.threshold))

        if result.baseline_path:
            text.append(t("diffscreen.baseline", path=result.baseline_path), style="dim")
        if result.screenshot_path:
            text.append(t("diffscreen.screenshot", path=result.screenshot_path), style="dim")
        if result.diff_path:
            text.append(t("diffscreen.diff_image", path=result.diff_path), style="dim")

        return text

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
