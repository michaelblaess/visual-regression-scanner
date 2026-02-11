"""Bestaetigungsdialog fuer den Site-Reset."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ResetConfirmScreen(ModalScreen[bool]):
    """Modal-Dialog zur Bestaetigung des Site-Resets."""

    DEFAULT_CSS = """
    ResetConfirmScreen {
        align: center middle;
    }

    ResetConfirmScreen > Vertical {
        width: 64;
        height: auto;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
    }

    ResetConfirmScreen #reset-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $warning;
        color: $text;
        margin-bottom: 1;
    }

    ResetConfirmScreen #reset-message {
        height: auto;
        padding: 1 2;
        margin-bottom: 1;
    }

    ResetConfirmScreen .button-row {
        height: auto;
        align: center middle;
        padding: 1 2;
    }

    ResetConfirmScreen .button-row Button {
        margin: 0 1;
        min-width: 16;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Ja", show=False),
        Binding("j", "confirm", "Ja", show=False),
        Binding("n", "cancel", "Nein", show=False),
        Binding("escape", "cancel", "Abbrechen", show=False),
    ]

    def __init__(self, hostname: str, file_count: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._hostname = hostname
        self._file_count = file_count

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout mit Buttons."""
        msg = (
            f"Alle Bilder fuer {self._hostname} werden geloescht!\n\n"
            f"Betroffen: {self._file_count} Dateien "
            f"(Baselines, Screenshots, Diffs)\n\n"
            f"Die Sitemap wird danach neu geladen."
        )

        with Vertical():
            yield Static("Reset", id="reset-title")
            yield Static(msg, id="reset-message")
            with Horizontal(classes="button-row"):
                yield Button("Loeschen", id="btn-reset-confirm", variant="error")
                yield Button("Abbrechen", id="btn-reset-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reagiert auf Button-Klicks.

        Args:
            event: Das Button-Pressed-Event.
        """
        if event.button.id == "btn-reset-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Bestaetigt den Reset (Tastatur y/j)."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Bricht den Reset ab (Tastatur n/ESC)."""
        self.dismiss(False)
