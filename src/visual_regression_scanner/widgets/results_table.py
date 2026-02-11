"""DataTable-Widget fuer Vergleichs-Ergebnisse."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Input, Static
from textual.message import Message
from rich.text import Text

from ..models.scan_result import ComparisonStatus, ScreenshotResult


class ResultsTable(Vertical):
    """Widget mit filterbarer DataTable fuer Vergleichs-Ergebnisse."""

    DEFAULT_CSS = """
    ResultsTable {
        height: 1fr;
    }

    ResultsTable #filter-bar {
        dock: top;
        height: 3;
        padding: 0 1;
    }

    ResultsTable #results-count {
        dock: top;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    ResultsTable DataTable {
        height: 1fr;
    }
    """

    filter_text: reactive[str] = reactive("")

    class ResultSelected(Message):
        """Wird gesendet wenn ein Ergebnis ausgewaehlt wird (Enter/Doppelklick)."""

        def __init__(self, result: ScreenshotResult) -> None:
            super().__init__()
            self.result = result

    class ResultHighlighted(Message):
        """Wird gesendet wenn der Cursor auf ein Ergebnis bewegt wird."""

        def __init__(self, result: ScreenshotResult) -> None:
            super().__init__()
            self.result = result

    # Spinner-Frames fuer SCANNING-Status
    SPINNER_FRAMES = [">  ", ">> ", ">>>", " >>", "  >", "   "]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._results: list[ScreenshotResult] = []
        self._filtered: list[ScreenshotResult] = []
        self._show_only_diffs: bool = False
        self._spinner_frame: int = 0
        self._spinner_timer = None

    def compose(self) -> ComposeResult:
        """Erstellt die Kind-Widgets."""
        yield Input(placeholder="Filter (URL, Status...)", id="filter-bar")
        yield Static("", id="results-count")
        yield DataTable(id="results-data", cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        """Initialisiert die Tabellenspalten und startet den Spinner-Timer."""
        table = self.query_one("#results-data", DataTable)
        table.add_columns("#", "Status", "URL", "HTTP", "Zeit", "Diff %")
        self._spinner_timer = self.set_interval(0.3, self._tick_spinner)

    def _tick_spinner(self) -> None:
        """Aktualisiert den Spinner-Frame und refresht die Tabelle wenn noetig."""
        has_scanning = any(r.status == ComparisonStatus.SCANNING for r in self._filtered)
        if not has_scanning:
            return
        self._spinner_frame = (self._spinner_frame + 1) % len(self.SPINNER_FRAMES)
        self._refresh_table()

    def load_results(self, results: list[ScreenshotResult]) -> None:
        """Laedt Ergebnisse in die Tabelle.

        Args:
            results: Liste der ScreenshotResults.
        """
        self._results = results
        self._apply_filter()

    def update_result(self, result: ScreenshotResult) -> None:
        """Aktualisiert ein einzelnes Ergebnis in der Tabelle.

        Args:
            result: Das aktualisierte ScreenshotResult.
        """
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Wendet den aktuellen Filter an und aktualisiert die Tabelle."""
        search = self.filter_text.lower()

        self._filtered = []
        for r in self._results:
            if self._show_only_diffs and r.status not in (
                ComparisonStatus.DIFF, ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT
            ):
                continue
            if search and search not in r.url.lower():
                continue
            self._filtered.append(r)

        self._refresh_table()

    def _refresh_table(self) -> None:
        """Aktualisiert die DataTable mit gefilterten Ergebnissen."""
        table = self.query_one("#results-data", DataTable)
        table.clear()

        for idx, result in enumerate(self._filtered):
            status_text = self._styled_status(result)

            scanned = result.status not in (ComparisonStatus.PENDING, ComparisonStatus.SCANNING)

            if scanned:
                diff_text = _colored_diff(result.diff_percentage, result.threshold, result.status)
            else:
                diff_text = Text("-", style="dim")

            http_code_str = str(result.http_status_code) if result.http_status_code > 0 else "-"
            time_str = f"{result.load_time_ms / 1000:.1f}s" if result.load_time_ms > 0 else "-"

            table.add_row(
                str(idx + 1),
                status_text,
                result.url,
                http_code_str,
                time_str,
                diff_text,
                key=str(idx),
            )

        count_label = self.query_one("#results-count", Static)
        total = len(self._results)
        shown = len(self._filtered)
        if total == shown:
            count_label.update(f" {total} URLs")
        else:
            count_label.update(f" {shown} von {total} URLs (gefiltert)")

    def _styled_status(self, result: ScreenshotResult) -> Text:
        """Erstellt farbcodierten Status-Text.

        Args:
            result: ScreenshotResult mit Status-Info.

        Returns:
            Farbcodierter Rich Text.
        """
        if result.status == ComparisonStatus.SCANNING:
            frame = self.SPINNER_FRAMES[self._spinner_frame % len(self.SPINNER_FRAMES)]
            return Text(frame, style="bold cyan")

        styles = {
            ComparisonStatus.PENDING: ("...", "dim"),
            ComparisonStatus.MATCH: ("OK", "bold green"),
            ComparisonStatus.DIFF: ("DIFF", "bold red"),
            ComparisonStatus.NEW_BASELINE: ("NEU", "bold blue"),
            ComparisonStatus.ERROR: ("ERR", "bold red"),
            ComparisonStatus.TIMEOUT: ("T/O", "bold yellow"),
        }
        icon, style = styles.get(result.status, ("?", ""))
        return Text(icon, style=style)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Reagiert auf Aenderungen im Filter-Input."""
        if event.input.id == "filter-bar":
            self.filter_text = event.value
            self._apply_filter()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Reagiert auf Enter/Klick auf eine Zeile."""
        idx = int(event.row_key.value)
        if 0 <= idx < len(self._filtered):
            self.post_message(self.ResultSelected(self._filtered[idx]))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Reagiert auf Cursor-Bewegung."""
        if event.row_key is None:
            return
        idx = int(event.row_key.value)
        if 0 <= idx < len(self._filtered):
            self.post_message(self.ResultHighlighted(self._filtered[idx]))

    def toggle_diff_filter(self) -> None:
        """Wechselt zwischen 'alle anzeigen' und 'nur Diffs'."""
        self._show_only_diffs = not self._show_only_diffs
        self._apply_filter()

    def get_selected_result(self) -> ScreenshotResult | None:
        """Gibt das aktuell ausgewaehlte Ergebnis zurueck.

        Returns:
            Aktuelles ScreenshotResult oder None.
        """
        table = self.query_one("#results-data", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            idx = int(row_key.value)
            if 0 <= idx < len(self._filtered):
                return self._filtered[idx]
        except Exception:
            pass
        return None


def _colored_diff(percentage: float, threshold: float, status: ComparisonStatus) -> Text:
    """Erstellt einen farbigen Diff-Prozent-Text.

    Args:
        percentage: Diff-Prozent.
        threshold: Schwelle.
        status: Aktueller Status.

    Returns:
        Farbcodierter Rich Text.
    """
    if status == ComparisonStatus.NEW_BASELINE:
        return Text("-", style="bold blue")
    if status in (ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT):
        return Text("-", style="dim")

    text = f"{percentage:.2f}%"
    if percentage > threshold:
        return Text(text, style="bold red")
    if percentage > 0:
        return Text(text, style="dim green")
    return Text("0.00%", style="dim green")
