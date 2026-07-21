"""Bildvorschau im Terminal: textual-image (TGP/Sixel) mit Halbblock-Ausweichweg.

Bis hierher liessen sich die Aufnahmen nur im Browser ansehen. Fuer den
schnellen Blick - hat sich diese Seite wirklich veraendert, oder ist es nur
Rauschen? - reicht das Terminal, wenn es Bilder darstellen kann.

Die grafische Darstellung ist bewusst abschaltbar: Auf manchen Terminals
stoert ein Sixel-Widget die uebrige Darstellung. Ohne sie wird das Bild aus
Unicode-Halbbloecken aufgebaut, was ueberall funktioniert.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any, cast

from PIL import Image as PILImage
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from ..i18n import t

_UPPER_HALF_BLOCK = "▀"


def select_graphics_backend() -> str | None:
    """Raet anhand der Umgebung, welches Bildverfahren das Terminal beherrscht.

    Returns:
        "tgp", "sixel" oder None fuer den Halbblock-Ausweichweg.
    """
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if os.environ.get("KITTY_WINDOW_ID") or "kitty" in term or "ghostty" in term:
        return "tgp"
    if term_program in ("wezterm", "ghostty") or os.environ.get("KONSOLE_VERSION"):
        return "tgp"
    if os.environ.get("WT_SESSION"):
        return "sixel"
    if term in ("foot", "xterm", "mlterm", "mintty") or term_program in ("mintty", "iterm.app"):
        return "sixel"
    return None


def _load_graphics_widget_class(backend: str | None) -> type[Widget] | None:
    """Laedt die Widget-Klasse zum gewaehlten Verfahren, oder None."""
    if backend is None:
        return None
    try:
        if backend == "tgp":
            from textual_image.widget import TGPImage

            return TGPImage
        from textual_image.widget import SixelImage

        return SixelImage
    except ImportError:
        return None


def render_half_blocks(path: str | Path, max_width: int, max_height: int) -> Text:
    """Baut ein Bild aus Unicode-Halbbloecken auf (zwei Bildpunkte je Zeichen).

    Args:
        path:
            Pfad zur Bilddatei.
        max_width:
            Verfuegbare Breite in Zeichen.
        max_height:
            Verfuegbare Hoehe in Zeilen.

    Returns:
        Eingefaerbter Text, der das Bild darstellt.
    """
    img = PILImage.open(path).convert("RGB")
    orig_w, orig_h = img.size
    pixel_h = max(2, max_height * 2)
    scale = min(max_width / orig_w, pixel_h / orig_h)
    new_w = max(1, int(orig_w * scale))
    new_h = max(2, int(orig_h * scale))
    if new_h % 2:
        new_h += 1
    img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)

    out = Text()
    for y in range(0, new_h, 2):
        for x in range(new_w):
            top = cast("tuple[int, int, int]", img.getpixel((x, y)))
            bottom = cast("tuple[int, int, int]", img.getpixel((x, y + 1)))
            out.append(
                _UPPER_HALF_BLOCK,
                style=f"rgb({top[0]},{top[1]},{top[2]}) on rgb({bottom[0]},{bottom[1]},{bottom[2]})",
            )
        out.append("\n")
    return out


class ImagePreview(Widget):
    """Zeigt eine Bilddatei im Terminal an."""

    DEFAULT_CSS = """
    ImagePreview {
        height: 1fr;
    }
    ImagePreview VerticalScroll {
        height: 1fr;
    }
    ImagePreview .preview-hint {
        color: $text-muted;
        padding: 1;
    }
    """

    def __init__(self, enabled_graphics: bool = False, **kwargs: Any) -> None:
        """Erstellt die Vorschau.

        Args:
            enabled_graphics:
                True = Sixel/TGP versuchen. False = immer Halbbloecke, was auf
                jedem Terminal sicher darstellbar ist.
        """
        super().__init__(**kwargs)
        self._backend = select_graphics_backend() if enabled_graphics else None
        self._graphics_class = _load_graphics_widget_class(self._backend)
        self._current: Path | None = None

    @property
    def backend_name(self) -> str:
        """Name des verwendeten Verfahrens - fuer Protokoll und Tests."""
        if self._graphics_class is None:
            return "halfblocks"
        return self._backend or "halfblocks"

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(t("preview.none"), classes="preview-hint", id="preview-body")

    def show_image(self, path: str | Path | None) -> None:
        """Zeigt die angegebene Bilddatei an.

        Args:
            path:
                Pfad zur Datei. None oder eine fehlende Datei leert die Anzeige.
        """
        container = self.query_one(VerticalScroll)
        self._clear(container)

        if path is None:
            container.mount(Static(t("preview.none"), classes="preview-hint"))
            return

        file_path = Path(path)
        if not file_path.is_file():
            container.mount(Static(t("preview.missing", name=file_path.name), classes="preview-hint"))
            return

        self._current = file_path
        if self._graphics_class is not None:
            with contextlib.suppress(Exception):
                # Die Bild-Widgets von textual-image nehmen den Pfad entgegen;
                # ihre Signatur ist fuer mypy nicht als Widget-Konstruktor lesbar.
                widget = cast("Any", self._graphics_class)(str(file_path))
                container.mount(widget)
                return

        # Ausweichweg: Halbbloecke in der verfuegbaren Flaeche.
        width = max(20, container.size.width - 2)
        height = max(10, container.size.height - 1)
        try:
            container.mount(Static(render_half_blocks(file_path, width, height)))
        except Exception:  # noqa: BLE001 - ein kaputtes Bild darf die App nicht beenden
            container.mount(Static(t("preview.unreadable", name=file_path.name), classes="preview-hint"))

    def clear(self) -> None:
        """Leert die Anzeige."""
        self._current = None
        self.show_image(None)

    def _clear(self, container: VerticalScroll) -> None:
        """Entfernt den bisherigen Inhalt."""
        for child in list(container.children):
            with contextlib.suppress(Exception):
                child.remove()
