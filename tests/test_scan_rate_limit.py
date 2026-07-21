"""Integrationstest: greift das Rate-Limit im echten Screenshot-Pfad?

Der Unit-Test in test_rate_limit.py prueft nur den Limiter selbst. Hier laeuft
Screenshotter.capture_urls() vollstaendig durch - lediglich der Browser-Start
und die eigentliche Aufnahme sind ersetzt, damit der Test ohne Playwright und
ohne Netzwerk auskommt. Faellt die Verdrahtung weg, sind gedrosselter und
ungedrosselter Lauf gleich schnell und der Test schlaegt fehl.
"""

from __future__ import annotations

import asyncio
import time

from visual_regression_scanner.models.scan_result import ScreenshotResult
from visual_regression_scanner.services import screenshotter as shot_module
from visual_regression_scanner.services.screenshotter import Screenshotter

_PAGE_COUNT = 5


class _FakePlaywright:
    """Ersetzt async_playwright(): liefert ein Objekt mit start()/stop()."""

    async def start(self) -> _FakePlaywright:
        return self

    async def stop(self) -> None:
        return None


def _capture_seconds(rate_per_minute: int, tmp_path, monkeypatch) -> float:  # type: ignore[no-untyped-def]
    """Misst einen kompletten Durchlauf ohne Browser und ohne Netzwerk."""
    monkeypatch.setattr(shot_module, "async_playwright", lambda: _FakePlaywright())

    shooter = Screenshotter(concurrency=4, timeout=5, rate_per_minute=rate_per_minute)

    async def fake_launch() -> object:
        return object()

    async def fake_capture(result: ScreenshotResult, output_dir: str, log: object) -> None:
        return None

    async def fake_close() -> None:
        return None

    monkeypatch.setattr(shooter, "_launch_browser", fake_launch)
    monkeypatch.setattr(shooter, "_capture_single_page", fake_capture)
    monkeypatch.setattr(shooter, "_cleanup", fake_close)

    results = [ScreenshotResult(url=f"https://example.com/seite-{i}") for i in range(_PAGE_COUNT)]

    start = time.monotonic()
    asyncio.run(shooter.capture_urls(results, str(tmp_path)))
    return time.monotonic() - start


class TestCaptureRateLimit:
    def test_unlimited_run_is_fast(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Referenzlauf: ohne Limit ist der Durchlauf in Sekundenbruchteilen fertig."""
        assert _capture_seconds(0, tmp_path, monkeypatch) < 1.0

    def test_rate_limit_slows_the_run_down(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """1200/Minute = 50 ms Abstand; fuenf Seiten warten also mehrere Intervalle."""
        # Untere Schranke mit Abstand zum Sollwert (200 ms): die Timeraufloesung
        # unter Windows liegt bei rund 15 ms, ein exakter Wert waere flaky.
        assert _capture_seconds(1200, tmp_path, monkeypatch) >= 0.15
