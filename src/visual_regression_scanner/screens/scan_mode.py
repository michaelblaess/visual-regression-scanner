"""Scan-Modus-Dialog - fragt wie mit vorhandenen Screenshots verfahren wird."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static


# Rueckgabewerte des Dialogs
SCAN_REPLACE = "replace"          # Option A: Nur neue Screenshots, Referenz bleibt
SCAN_UPDATE_BASELINE = "update"   # Option B: Current → Referenz, dann neuer Scan
SCAN_CANCEL = None                # Abgebrochen


class _OptionWidget(Widget):
    """Rendert eine Scan-Option mit Beschreibung und Workflow-Diagramm."""

    DEFAULT_CSS = """
    _OptionWidget {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, text: Text, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = text

    def render(self) -> Text:
        """Rendert den Option-Text."""
        return self._text


class ScanModeScreen(ModalScreen[str | None]):
    """Dialog zur Auswahl des Scan-Modus.

    Wird angezeigt wenn bereits Referenz-Bilder UND aktuelle
    Screenshots vorhanden sind.
    """

    DEFAULT_CSS = """
    ScanModeScreen {
        align: center middle;
    }

    ScanModeScreen > Vertical {
        width: 72;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    ScanModeScreen #scan-mode-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    ScanModeScreen #scan-mode-intro {
        height: auto;
        padding: 0 2 1 2;
    }

    ScanModeScreen .option-box {
        height: auto;
        background: $surface-darken-1;
        border: solid $primary-darken-1;
        padding: 1 1;
        margin: 0 1 1 1;
    }

    ScanModeScreen .option-box Button {
        margin: 1 1 0 1;
        width: 100%;
    }

    ScanModeScreen #btn-scan-cancel {
        margin: 0 1;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("a", "option_a", "Option A", show=False),
        Binding("b", "option_b", "Option B", show=False),
        Binding("escape", "cancel", "Abbrechen", show=False),
    ]

    def __init__(self, baseline_count: int, current_count: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._baseline_count = baseline_count
        self._current_count = current_count

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout mit zwei Optionen."""
        intro = (
            f"Es sind bereits {self._baseline_count} Referenz-Bilder und "
            f"{self._current_count} aktuelle Screenshots vorhanden.\n\n"
            f"Wie soll der neue Scan verfahren?"
        )

        with Vertical():
            yield Static("Scan-Modus", id="scan-mode-title")
            yield Static(intro, id="scan-mode-intro")

            # Option A
            with Vertical(classes="option-box"):
                yield _OptionWidget(_build_option_a_text())
                yield Button(
                    "A: Erneut scannen",
                    id="btn-option-a",
                    variant="primary",
                )

            # Option B
            with Vertical(classes="option-box"):
                yield _OptionWidget(_build_option_b_text())
                yield Button(
                    "B: Referenz aktualisieren + scannen",
                    id="btn-option-b",
                    variant="warning",
                )

            yield Button("Abbrechen", id="btn-scan-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reagiert auf Button-Klicks.

        Args:
            event: Das Button-Pressed-Event.
        """
        if event.button.id == "btn-option-a":
            self.dismiss(SCAN_REPLACE)
        elif event.button.id == "btn-option-b":
            self.dismiss(SCAN_UPDATE_BASELINE)
        else:
            self.dismiss(SCAN_CANCEL)

    def action_option_a(self) -> None:
        """Waehlt Option A (Taste a)."""
        self.dismiss(SCAN_REPLACE)

    def action_option_b(self) -> None:
        """Waehlt Option B (Taste b)."""
        self.dismiss(SCAN_UPDATE_BASELINE)

    def action_cancel(self) -> None:
        """Bricht ab (Taste ESC)."""
        self.dismiss(SCAN_CANCEL)


def _build_option_a_text() -> Text:
    """Erzeugt den Beschreibungstext fuer Option A.

    Returns:
        Rich Text mit Beschreibung und Workflow-Diagramm.
    """
    text = Text()
    text.append("Erneut scannen\n", style="bold")
    text.append("Neue Screenshots ersetzen die aktuellen.\n", style="dim")
    text.append("Die Referenz bleibt unveraendert.\n\n", style="dim")

    #  Workflow-Diagramm
    text.append("  Referenz (Baseline)\n", style="bold cyan")
    text.append("    |  bleibt unveraendert\n", style="dim")
    text.append("    |\n", style="dim")
    text.append("    +--< Vergleich >--+\n", style="bold")
    text.append("                      |\n", style="dim")
    text.append("  Neuer Scan ", style="bold green")
    text.append("----------+\n", style="dim")
    text.append("    ersetzt aktuelle Screenshots\n", style="dim")

    return text


def _build_option_b_text() -> Text:
    """Erzeugt den Beschreibungstext fuer Option B.

    Returns:
        Rich Text mit Beschreibung und Workflow-Diagramm.
    """
    text = Text()
    text.append("Referenz aktualisieren + scannen\n", style="bold")
    text.append("Die aktuellen Screenshots werden zur neuen Referenz.\n", style="dim")
    text.append("Dann wird ein neuer Scan durchgefuehrt.\n\n", style="dim")

    # Workflow-Diagramm
    text.append("  Alte Referenz ", style="dim")
    text.append("x geloescht\n", style="bold red")
    text.append("  Aktuelle Screenshots ", style="bold yellow")
    text.append("---> ", style="bold")
    text.append("neue Referenz\n", style="bold cyan")
    text.append("    |\n", style="dim")
    text.append("    +--< Vergleich >--+\n", style="bold")
    text.append("                      |\n", style="dim")
    text.append("  Neuer Scan ", style="bold green")
    text.append("----------+\n", style="dim")
    text.append("    wird zu aktuellen Screenshots\n", style="dim")

    return text
