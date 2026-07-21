"""Auswahl-Dialog fuer den Verlauf der geprueften Sitemaps."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from ..i18n import t
from ..models.history import History, HistoryEntry


class HistoryScreen(ModalScreen[HistoryEntry | None]):
    """Zeigt frueher gepruefte Sitemaps zur Auswahl.

    Liefert den gewaehlten Eintrag zurueck oder None bei Abbruch.
    """

    BINDINGS = [
        Binding("escape", "cancel", t("binding.close")),
        Binding("enter", "select", t("binding.select")),
    ]

    DEFAULT_CSS = """
    HistoryScreen {
        align: center middle;
    }
    HistoryScreen > Vertical {
        width: 92;
        max-width: 96%;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    HistoryScreen #history-title {
        text-style: bold;
        padding-bottom: 1;
    }
    HistoryScreen #history-empty {
        color: $text-muted;
        padding: 1 0;
    }
    HistoryScreen #history-buttons {
        height: auto;
        padding-top: 1;
        align-horizontal: right;
    }
    HistoryScreen #history-buttons Button {
        margin-left: 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[HistoryEntry] = History.load()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(t("history.title"), id="history-title")
            if self._entries:
                yield DataTable(id="history-table", cursor_type="row", zebra_stripes=True)
            else:
                yield Static(t("history.empty"), id="history-empty")
            with Horizontal(id="history-buttons"):
                yield Button(t("history.btn.close"), variant="default", id="history-close")
                if self._entries:
                    yield Button(t("history.btn.select"), variant="primary", id="history-select")

    def on_mount(self) -> None:
        """Fuellt die Tabelle mit den gespeicherten Eintraegen."""
        if not self._entries:
            return
        table = self.query_one("#history-table", DataTable)
        table.add_columns(
            t("history.col.sitemap"),
            t("history.col.when"),
            t("history.col.viewport"),
            t("history.col.result"),
        )
        for entry in self._entries:
            table.add_row(
                entry.url,
                entry.display_time,
                entry.viewport or "-",
                entry.display_result,
            )
        table.focus()

    def _selected(self) -> HistoryEntry | None:
        """Liefert den Eintrag der markierten Zeile."""
        if not self._entries:
            return None
        table = self.query_one("#history-table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def action_select(self) -> None:
        """Uebernimmt die markierte Zeile."""
        self.dismiss(self._selected())

    def action_cancel(self) -> None:
        """Bricht ohne Auswahl ab."""
        self.dismiss(None)

    @on(DataTable.RowSelected)
    def _on_row_selected(self) -> None:
        self.dismiss(self._selected())

    @on(Button.Pressed, "#history-select")
    def _on_select_pressed(self) -> None:
        self.dismiss(self._selected())

    @on(Button.Pressed, "#history-close")
    def _on_close_pressed(self) -> None:
        self.dismiss(None)
