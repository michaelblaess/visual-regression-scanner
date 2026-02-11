"""About-Screen fuer Visual Regression Scanner."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult, RenderResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static

from .. import __author__, __version__, __year__


class AboutContent(Widget):
    """Rendert den About-Inhalt als Rich Text."""

    DEFAULT_CSS = """
    AboutContent {
        height: auto;
        padding: 1 2;
    }
    """

    def render(self) -> RenderResult:
        """Erstellt den About-Text."""
        text = Text()
        text.append(f"v{__version__}", style="bold")
        text.append("  \u00b7  ", style="dim")
        text.append(__author__, style="bold")
        text.append("  \u00b7  ", style="dim")
        text.append(__year__, style="bold")
        text.append("\n\n")

        text.append("Erkennt visuelle Aenderungen auf Websites\n")
        text.append("durch automatischen Screenshot-Vergleich.\n\n")
        text.append("Eingabe: Sitemap-URL (XML)\n")
        text.append("Ausgabe: TUI + HTML/JSON Reports mit Diff-Bildern\n\n")

        text.append("\u2500" * 44 + "\n\n", style="dim")

        text.append(
            "\u201eWir muessen lernen, entweder als\n"
            "Brueder miteinander zu leben oder\n"
            "als Narren unterzugehen.\u201c\n\n",
            style="italic",
        )
        text.append("  \u2014 Martin Luther King Jr.", style="bold")

        return text


class AboutScreen(ModalScreen):
    """Modal-Dialog mit Informationen ueber die Anwendung."""

    DEFAULT_CSS = """
    AboutScreen {
        align: center middle;
    }

    AboutScreen > VerticalScroll {
        width: 60;
        height: 30;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    AboutScreen #about-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }

    AboutScreen #about-footer {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Schliessen"),
        Binding("q", "close", "Schliessen"),
    ]

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        with VerticalScroll():
            yield Static("Visual Regression Scanner", id="about-title")
            yield AboutContent()
            yield Static("ESC = Schliessen", id="about-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
