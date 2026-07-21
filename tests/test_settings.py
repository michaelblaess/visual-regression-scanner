"""Tests fuer die persistenten Einstellungen und ihre Rangfolge.

Der wichtigste Test hier ist die Rangfolge: Angaben auf der Kommandozeile
muessen die gespeicherten Werte fuer den laufenden Aufruf schlagen, ohne die
Datei zu veraendern - und ohne Angabe muss der gespeicherte Wert gelten. Ohne
diese Pruefung wuerden die Vorgaben der Kommandozeile die Einstellungen bei
jedem Start ueberschreiben und der Dialog waere wirkungslos.
"""

from __future__ import annotations

import json
from pathlib import Path

from visual_regression_scanner.app import VisualRegressionScannerApp
from visual_regression_scanner.models.settings import Settings, parse_cookies

_SITEMAP = "https://example.com/sitemap.xml"


class TestDefaults:
    def test_rate_limit_is_on(self) -> None:
        assert Settings().rate_limit_enabled is True

    def test_rate_default(self) -> None:
        assert Settings().rate_per_minute == 60

    def test_robots_is_respected(self) -> None:
        assert Settings().respect_robots is True

    def test_full_page_is_on(self) -> None:
        assert Settings().full_page is True


class TestPersistence:
    def test_roundtrip(self, _isolated_settings: Path) -> None:
        original = Settings()
        original.threshold = 0.75
        original.rate_per_minute = 20
        original.rate_limit_enabled = False
        original.viewport = "1280x720"
        original.save()

        loaded = Settings.load()
        assert loaded.threshold == 0.75
        assert loaded.rate_per_minute == 20
        assert loaded.rate_limit_enabled is False
        assert loaded.viewport == "1280x720"

    def test_missing_file_gives_defaults(self, _isolated_settings: Path) -> None:
        assert not _isolated_settings.exists()
        assert Settings.load().rate_per_minute == 60

    def test_broken_file_gives_defaults(self, _isolated_settings: Path) -> None:
        """Eine kaputte Datei darf den Start nicht verhindern."""
        _isolated_settings.write_text("kein JSON", encoding="utf-8")
        assert Settings.load().rate_per_minute == 60

    def test_garbage_numbers_are_ignored(self, _isolated_settings: Path) -> None:
        """Von Hand verstellte Zahlenwerte fallen auf die Vorgabe zurueck."""
        _isolated_settings.write_text(json.dumps({"concurrency": "viele", "timeout": None}), encoding="utf-8")
        loaded = Settings.load()
        assert loaded.concurrency == 4
        assert loaded.timeout == 30


class TestPrecedence:
    """Kommandozeile schlaegt Einstellungen - aber nur, wenn etwas angegeben ist."""

    def test_stored_values_apply_without_cli(self, _isolated_settings: Path) -> None:
        stored = Settings()
        stored.concurrency = 2
        stored.rate_per_minute = 30
        stored.threshold = 0.9
        stored.save()

        app = VisualRegressionScannerApp(sitemap_url=_SITEMAP)
        assert app.concurrency == 2
        assert app.rate_per_minute == 30
        assert app.threshold == 0.9

    def test_cli_overrides_stored_values(self, _isolated_settings: Path) -> None:
        stored = Settings()
        stored.concurrency = 2
        stored.rate_per_minute = 30
        stored.save()

        app = VisualRegressionScannerApp(sitemap_url=_SITEMAP, concurrency=16, rate_per_minute=0)
        assert app.concurrency == 16
        assert app.rate_per_minute == 0

    def test_disabled_rate_limit_means_zero(self, _isolated_settings: Path) -> None:
        """Abgeschaltet in den Einstellungen entspricht 0 Aufrufen pro Minute."""
        stored = Settings()
        stored.rate_limit_enabled = False
        stored.rate_per_minute = 60
        stored.save()

        assert VisualRegressionScannerApp(sitemap_url=_SITEMAP).rate_per_minute == 0

    def test_viewport_from_settings_is_parsed(self, _isolated_settings: Path) -> None:
        stored = Settings()
        stored.viewport = "1280x720"
        stored.save()

        app = VisualRegressionScannerApp(sitemap_url=_SITEMAP)
        assert (app.viewport_width, app.viewport_height) == (1280, 720)


class TestCookieParsing:
    def test_single_cookie(self) -> None:
        assert parse_cookies("auth=token") == [{"name": "auth", "value": "token"}]

    def test_multiple_cookies(self) -> None:
        assert len(parse_cookies("a=1, b=2")) == 2

    def test_entries_without_equals_are_skipped(self) -> None:
        assert parse_cookies("kaputt, a=1") == [{"name": "a", "value": "1"}]

    def test_empty_string(self) -> None:
        assert parse_cookies("") == []

    def test_value_may_contain_equals(self) -> None:
        assert parse_cookies("t=a=b") == [{"name": "t", "value": "a=b"}]
