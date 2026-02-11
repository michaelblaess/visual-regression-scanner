"""Detail-Ansicht fuer Diff-Informationen einer gescannten URL."""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static

from ..models.scan_result import ComparisonStatus, ScreenshotResult


class DiffDetailView(Widget):
    """Zeigt die Diff-Details einer ausgewaehlten URL mit Timestamps und Buttons."""

    DEFAULT_CSS = """
    DiffDetailView {
        height: 1fr;
        background: $surface;
        border-left: solid $accent;
        overflow-y: scroll;
        scrollbar-gutter: stable;
    }

    DiffDetailView #detail-content {
        padding: 1 2;
    }

    DiffDetailView .file-row {
        height: auto;
        padding: 0 2;
        margin-bottom: 1;
    }

    DiffDetailView .file-row .file-info {
        height: auto;
        width: 1fr;
    }

    DiffDetailView .file-row Button {
        min-width: 10;
        height: 3;
        margin-left: 1;
    }

    DiffDetailView #btn-open-images {
        margin: 0 2 1 2;
        width: auto;
    }
    """

    class OpenImagesRequested(Message):
        """Wird gesendet wenn der Benutzer die Bilder oeffnen moechte."""

        def __init__(self, result: ScreenshotResult) -> None:
            super().__init__()
            self.result = result

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._result: ScreenshotResult | None = None

    def compose(self) -> ComposeResult:
        """Erstellt das Widget-Layout."""
        with Vertical():
            yield Static(
                Text("Keine URL ausgewaehlt.\n\nWaehle eine URL in der Tabelle aus.", style="dim italic"),
                id="detail-content",
            )

            # Datei-Zeilen: Label + Pfad + Oeffnen-Button
            with Horizontal(classes="file-row", id="row-baseline"):
                yield Static(id="info-baseline", classes="file-info")
                yield Button("Oeffnen", id="btn-open-baseline", variant="default")

            with Horizontal(classes="file-row", id="row-screenshot"):
                yield Static(id="info-screenshot", classes="file-info")
                yield Button("Oeffnen", id="btn-open-screenshot", variant="default")

            with Horizontal(classes="file-row", id="row-diff"):
                yield Static(id="info-diff", classes="file-info")
                yield Button("Oeffnen", id="btn-open-diff", variant="default")

            yield Button(
                "Alle Bilder im Browser vergleichen",
                id="btn-open-images",
                variant="primary",
            )

    def on_mount(self) -> None:
        """Versteckt alle Buttons initial."""
        self._hide_file_rows()
        self.query_one("#btn-open-images", Button).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reagiert auf Button-Klicks.

        Args:
            event: Das Button-Pressed-Event.
        """
        if event.button.id == "btn-open-images" and self._result:
            self.post_message(self.OpenImagesRequested(self._result))
        elif event.button.id == "btn-open-baseline" and self._result:
            _open_file(self._result.baseline_path)
        elif event.button.id == "btn-open-screenshot" and self._result:
            _open_file(self._result.screenshot_path)
        elif event.button.id == "btn-open-diff" and self._result:
            _open_file(self._result.diff_path)

    def show_result(self, result: ScreenshotResult) -> None:
        """Zeigt die Details eines Vergleichs-Ergebnisses.

        Args:
            result: Das anzuzeigende ScreenshotResult.
        """
        self._result = result
        content = self.query_one("#detail-content", Static)
        content.update(self._build_text())
        self._update_file_rows(result)

    def clear(self) -> None:
        """Leert die Detail-Ansicht."""
        self._result = None
        content = self.query_one("#detail-content", Static)
        content.update(
            Text("Keine URL ausgewaehlt.\n\nWaehle eine URL in der Tabelle aus.", style="dim italic")
        )
        self._hide_file_rows()
        self.query_one("#btn-open-images", Button).display = False

    def refresh_content(self) -> None:
        """Aktualisiert den Inhalt (z.B. bei Live-Updates waehrend Scan)."""
        if self._result:
            self.show_result(self._result)

    def _hide_file_rows(self) -> None:
        """Versteckt alle Datei-Zeilen."""
        for row_id in ("row-baseline", "row-screenshot", "row-diff"):
            try:
                self.query_one(f"#{row_id}").display = False
            except Exception:
                pass

    def _update_file_rows(self, result: ScreenshotResult) -> None:
        """Aktualisiert die Datei-Zeilen mit Pfaden, Timestamps und Buttons.

        Args:
            result: Das ScreenshotResult mit Pfaden.
        """
        has_files = False

        # Baseline
        if result.baseline_path and os.path.exists(result.baseline_path):
            has_files = True
            timestamp = _get_file_timestamp(result.baseline_path)
            label = "Referenz (Baseline)"
            if timestamp:
                label += f"  ({timestamp})"
            info = self.query_one("#info-baseline", Static)
            info.update(Text.assemble(
                (f"{label}\n", "bold"),
                (result.baseline_path, "dim"),
            ))
            self.query_one("#row-baseline").display = True
        else:
            self.query_one("#row-baseline").display = False

        # Screenshot
        if result.screenshot_path and os.path.exists(result.screenshot_path):
            has_files = True
            timestamp = _get_file_timestamp(result.screenshot_path)
            label = "Aktueller Screenshot"
            if timestamp:
                label += f"  ({timestamp})"
            info = self.query_one("#info-screenshot", Static)
            info.update(Text.assemble(
                (f"{label}\n", "bold"),
                (result.screenshot_path, "dim"),
            ))
            self.query_one("#row-screenshot").display = True
        else:
            self.query_one("#row-screenshot").display = False

        # Diff
        if result.diff_path and os.path.exists(result.diff_path):
            has_files = True
            info = self.query_one("#info-diff", Static)
            info.update(Text.assemble(
                ("Diff\n", "bold"),
                (result.diff_path, "dim"),
            ))
            self.query_one("#row-diff").display = True
        else:
            self.query_one("#row-diff").display = False

        # "Alle Bilder vergleichen"-Button
        btn = self.query_one("#btn-open-images", Button)
        btn.display = has_files

    def _build_text(self) -> Text:
        """Erzeugt den Rich-Text fuer die Detail-Ansicht (ohne Datei-Bereich).

        Returns:
            Formatierter Text mit allen Diff-Details.
        """
        result = self._result
        if not result:
            return Text("Keine URL ausgewaehlt.", style="dim italic")

        text = Text()

        # URL-Header
        text.append("URL\n", style="bold underline")
        text.append(f"{result.url}\n\n", style="bold cyan")

        # Status-Zeile
        text.append("Status: ", style="bold")
        status_style = {
            ComparisonStatus.MATCH: "bold green",
            ComparisonStatus.DIFF: "bold red",
            ComparisonStatus.NEW_BASELINE: "bold blue",
            ComparisonStatus.ERROR: "bold red",
            ComparisonStatus.TIMEOUT: "bold yellow",
            ComparisonStatus.SCANNING: "bold cyan",
            ComparisonStatus.PENDING: "dim",
        }.get(result.status, "")
        text.append(f"{result.status_icon}", style=status_style)

        if result.http_status_code > 0:
            text.append(f"  |  HTTP {result.http_status_code}")

        if result.load_time_ms > 0:
            load_s = result.load_time_ms / 1000
            text.append(f"  |  {load_s:.1f}s")

        if result.retry_count > 0:
            text.append(f"  |  {result.retry_count} Retries", style="yellow")

        text.append("\n\n")

        # Diff-Informationen
        if result.status == ComparisonStatus.SCANNING:
            text.append("Screenshot wird erstellt...", style="cyan")
            return text

        if result.status == ComparisonStatus.PENDING:
            text.append("Noch nicht gescannt.", style="dim")
            return text

        if result.status == ComparisonStatus.NEW_BASELINE:
            text.append("Neue Referenz\n", style="bold blue underline")
            text.append("Keine vorherige Referenz vorhanden.\n")
            text.append("Screenshot wurde als neue Referenz gespeichert.\n\n")
            return text

        if result.status in (ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT):
            text.append("Fehler\n", style="bold red underline")
            text.append(f"{result.error_message}\n", style="red")
            return text

        # MATCH oder DIFF
        text.append("Vergleich\n", style="bold underline")
        text.append("\n")

        # Diff-Prozent
        text.append("Diff: ", style="bold")
        diff_style = "bold red" if result.is_diff else "bold green"
        text.append(f"{result.diff_percentage:.4f}%", style=diff_style)
        text.append("\n")

        # Pixel-Info
        text.append("Geaenderte Pixel: ", style="bold")
        text.append(f"{result.diff_pixel_count:,}")
        text.append(f" von {result.total_pixel_count:,}", style="dim")
        text.append("\n")

        # Threshold
        text.append("Threshold: ", style="bold")
        text.append(f"{result.threshold}%")
        text.append("\n")

        # Ergebnis
        text.append("Ergebnis: ", style="bold")
        if result.is_diff:
            text.append(
                f"{result.diff_percentage:.4f}% > {result.threshold}% ",
                style="bold red",
            )
            text.append("VISUELLER UNTERSCHIED", style="bold red")
        else:
            text.append(
                f"{result.diff_percentage:.4f}% <= {result.threshold}% ",
                style="bold green",
            )
            text.append("IDENTISCH", style="bold green")

        text.append("\n\n")
        text.append("Dateien\n", style="bold underline")

        return text


def _open_file(path: str) -> None:
    """Oeffnet eine Datei mit dem Standard-Programm des Betriebssystems.

    Args:
        path: Pfad zur Datei.
    """
    if not path or not os.path.exists(path):
        return

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _get_file_timestamp(path: str) -> str:
    """Liest den Aenderungszeitpunkt einer Datei und formatiert ihn.

    Args:
        path: Pfad zur Datei.

    Returns:
        Formatierter Timestamp (TT.MM.YYYY HH:MM:SS) oder leerer String.
    """
    try:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        pass
    return ""
