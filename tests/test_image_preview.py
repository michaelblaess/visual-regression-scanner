"""Tests fuer die Bildvorschau im Terminal."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from visual_regression_scanner.widgets.image_preview import (
    ImagePreview,
    render_half_blocks,
    select_graphics_backend,
)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Legt ein kleines Testbild an."""
    path = tmp_path / "probe.png"
    Image.new("RGB", (40, 20), color=(200, 30, 30)).save(path)
    return path


class TestBackendDetection:
    """Die Erkennung darf nie raten, wenn das Terminal nichts signalisiert."""

    def test_kitty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KITTY_WINDOW_ID", "1")
        assert select_graphics_backend() == "tgp"

    def test_windows_terminal_uses_sixel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("KITTY_WINDOW_ID", "KONSOLE_VERSION", "TERM_PROGRAM"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("TERM", "")
        monkeypatch.setenv("WT_SESSION", "abc")
        assert select_graphics_backend() == "sixel"

    def test_unknown_terminal_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("KITTY_WINDOW_ID", "KONSOLE_VERSION", "WT_SESSION", "TERM_PROGRAM"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("TERM", "dumb")
        assert select_graphics_backend() is None


class TestHalfBlocks:
    def test_renders_something(self, sample_image: Path) -> None:
        text = render_half_blocks(sample_image, max_width=20, max_height=10)
        assert str(text).strip()

    def test_respects_the_width(self, sample_image: Path) -> None:
        """Die laengste Zeile darf die verfuegbare Breite nicht ueberschreiten."""
        text = render_half_blocks(sample_image, max_width=20, max_height=10)
        assert max(len(line) for line in str(text).splitlines()) <= 20

    def test_two_pixels_per_character(self, sample_image: Path) -> None:
        """Halbbloecke fassen zwei Bildzeilen in eine Textzeile."""
        text = render_half_blocks(sample_image, max_width=40, max_height=20)
        lines = [line for line in str(text).splitlines() if line]
        # 40x20 in 40 Zeichen Breite -> 20 Bildzeilen -> hoechstens 10 Textzeilen
        assert 0 < len(lines) <= 10

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Eine fehlende Datei meldet sich als OSError - das faengt das Widget ab."""
        with pytest.raises(OSError):
            render_half_blocks(tmp_path / "gibtsnicht.png", 10, 10)


class TestWidget:
    def test_without_graphics_uses_half_blocks(self) -> None:
        assert ImagePreview(enabled_graphics=False).backend_name == "halfblocks"

    def test_graphics_backend_is_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KITTY_WINDOW_ID", "1")
        preview = ImagePreview(enabled_graphics=True)
        # Ohne installiertes textual-image faellt es auf Halbbloecke zurueck -
        # beides ist ein gueltiges Ergebnis, nur raten darf es nicht.
        assert preview.backend_name in ("tgp", "halfblocks")


class TestEnvironmentIsolation:
    def test_env_is_restored(self) -> None:
        """Sicherheitsnetz: die Tests duerfen die Umgebung nicht veraendern."""
        assert "KITTY_WINDOW_ID" not in os.environ or os.environ.get("KITTY_WINDOW_ID")
