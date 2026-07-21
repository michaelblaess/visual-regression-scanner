"""Sichert die schonenden Vorgabewerte und die Sprachwahl ab.

Diese Tests halten die Zusicherung fest, dass ein Lauf ohne weitere Angaben
gedrosselt ist und robots.txt beachtet - und dass beim Erststart niemand einen
Rechtstext in einer fremden Sprache vorgesetzt bekommt.
"""

from __future__ import annotations

import locale

from visual_regression_scanner.app import VisualRegressionScannerApp
from visual_regression_scanner.i18n import detect_language
from visual_regression_scanner.services.rate_limit import RateLimiter
from visual_regression_scanner.services.screenshotter import Screenshotter

_SITEMAP = "https://example.com/sitemap.xml"


class TestSafeDefaults:
    def test_screenshotter_is_throttled_by_default(self) -> None:
        assert Screenshotter().rate_per_minute == 60

    def test_screenshotter_limiter_is_active_by_default(self) -> None:
        assert RateLimiter(Screenshotter().rate_per_minute).enabled is True

    def test_app_is_throttled_by_default(self) -> None:
        assert VisualRegressionScannerApp(sitemap_url=_SITEMAP).rate_per_minute == 60

    def test_app_respects_robots_by_default(self) -> None:
        assert VisualRegressionScannerApp(sitemap_url=_SITEMAP).respect_robots is True

    def test_rate_can_be_switched_off_explicitly(self) -> None:
        app = VisualRegressionScannerApp(sitemap_url=_SITEMAP, rate_per_minute=0)
        assert app.rate_per_minute == 0
        assert RateLimiter(app.rate_per_minute).enabled is False


class TestCommandLineDefaults:
    """Die Vorgaben der Kommandozeile muessen zu denen der App passen."""

    def test_cli_without_rate_limit_leaves_it_to_the_settings(self) -> None:
        """Ohne Angabe liefert die Kommandozeile None - dann gilt die Einstellung.

        Ein fester Vorgabewert hier wuerde die gespeicherte Einstellung bei
        jedem Start ueberschreiben und den Dialog wirkungslos machen.
        """
        from visual_regression_scanner.__main__ import _build_parser

        args = _build_parser().parse_args([_SITEMAP])
        assert args.rate_limit is None

    def test_cli_respects_robots_by_default(self) -> None:
        from visual_regression_scanner.__main__ import _build_parser

        args = _build_parser().parse_args([_SITEMAP])
        assert args.ignore_robots is False

    def test_cli_allows_turning_the_limit_off(self) -> None:
        from visual_regression_scanner.__main__ import _build_parser

        args = _build_parser().parse_args([_SITEMAP, "--rate-limit", "0"])
        assert args.rate_limit == 0


class TestLanguageDetection:
    def test_german_environment(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("de_DE", "UTF-8"))
        assert detect_language() == "de"

    def test_english_environment(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("en_US", "UTF-8"))
        assert detect_language() == "en"

    def test_other_language_falls_back_to_english(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("pt_BR", "UTF-8"))
        assert detect_language() == "en"

    def test_broken_locale_falls_back_to_english(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """locale.getlocale() wirft auf manchen Systemen ValueError."""

        def boom(*args: object) -> tuple[str, str]:
            raise ValueError("unknown locale")

        monkeypatch.setattr(locale, "getlocale", boom)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        assert detect_language() == "en"
