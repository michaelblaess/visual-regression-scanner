"""Screenshotter-Service - Erstellt Screenshots mit Playwright."""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from ..models.scan_result import ComparisonStatus, ScreenshotResult


class Screenshotter:
    """Erstellt Full-Page-Screenshots von Webseiten.

    Verwendet Playwright (headless Chromium) fuer Browser-Automation.
    Unterstuetzt parallelen Scan mit konfigurierbarer Concurrency.
    """

    MAX_RETRIES = 3
    BACKOFF_BASE_SECONDS = 5

    # Realistischer Chrome User-Agent (kein HeadlessChrome, kein Playwright)
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        concurrency: int = 4,
        timeout: int = 30,
        headless: bool = True,
        user_agent: str = "",
        cookies: Optional[list[dict[str, str]]] = None,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True,
    ) -> None:
        self.concurrency = concurrency
        self.timeout = timeout
        self.headless = headless
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.cookies = cookies or []
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.full_page = full_page
        self._cancelled = False
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def capture_urls(
        self,
        results: list[ScreenshotResult],
        output_dir: str,
        on_result: Optional[Callable[[ScreenshotResult], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> list[ScreenshotResult]:
        """Erstellt Screenshots aller URLs parallel mit Semaphore-Begrenzung.

        Args:
            results: Liste der ScreenshotResult-Objekte (werden in-place aktualisiert).
            output_dir: Verzeichnis fuer die Screenshots.
            on_result: Callback fuer jedes einzelne Ergebnis.
            on_log: Callback fuer Log-Nachrichten.
            on_progress: Callback fuer Fortschritt (aktuell, gesamt).

        Returns:
            Die uebergebene Liste der ScreenshotResults.
        """
        self._cancelled = False
        total = len(results)
        semaphore = asyncio.Semaphore(self.concurrency)
        completed = 0

        # Screenshot-Verzeichnis erstellen
        os.makedirs(output_dir, exist_ok=True)

        def log(msg: str) -> None:
            if on_log:
                on_log(msg)

        log(
            f"Starte Screenshots von {total} URLs "
            f"(Concurrency: {self.concurrency}, Timeout: {self.timeout}s, "
            f"Viewport: {self.viewport_width}x{self.viewport_height})"
        )

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._launch_browser()
            log("Browser gestartet")

            async def capture_with_semaphore(result: ScreenshotResult, index: int) -> None:
                nonlocal completed
                if self._cancelled:
                    return

                async with semaphore:
                    if self._cancelled:
                        return

                    result.status = ComparisonStatus.SCANNING
                    if on_result:
                        on_result(result)

                    log(f"Screenshot ({index + 1}/{total}): {result.url}")
                    await self._capture_single_page(result, output_dir, log)
                    completed += 1

                    if on_result:
                        on_result(result)
                    if on_progress:
                        on_progress(completed, total)

                    status_text = result.status_icon
                    log(f"  [{status_text}] {result.url} ({result.load_time_ms / 1000:.1f}s)")

            tasks = [
                capture_with_semaphore(result, idx)
                for idx, result in enumerate(results)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            log(f"[red]Kritischer Fehler: {e}[/red]")
        finally:
            await self._cleanup()
            log("Browser geschlossen")

        return results

    async def _capture_single_page(
        self,
        result: ScreenshotResult,
        output_dir: str,
        log: Callable[[str], None],
    ) -> None:
        """Erstellt einen Screenshot einer einzelnen Seite mit Retry-Logik.

        Args:
            result: ScreenshotResult das befuellt wird.
            output_dir: Verzeichnis fuer den Screenshot.
            log: Logging-Callback.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                await self._do_capture_page(result, output_dir, log)
                return
            except Exception as e:
                result.retry_count = attempt + 1
                error_msg = str(e)

                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BACKOFF_BASE_SECONDS * (2 ** attempt)
                    log(f"  Retry {attempt + 1}/{self.MAX_RETRIES} fuer {result.url} in {wait_time}s ({error_msg})")

                    # Netzwerk-Check vor Retry
                    if not await self._check_network():
                        log("  Warte auf Netzwerk...")
                        await self._wait_for_network(max_wait=wait_time * 2)

                    await asyncio.sleep(wait_time)

                    # Browser-Recovery falls noetig
                    if not self._browser or not self._browser.is_connected():
                        log("  Browser-Recovery...")
                        try:
                            self._browser = await self._launch_browser()
                        except Exception as browser_err:
                            log(f"  Browser-Recovery fehlgeschlagen: {browser_err}")
                else:
                    # Letzter Versuch fehlgeschlagen
                    if "timeout" in error_msg.lower():
                        result.status = ComparisonStatus.TIMEOUT
                    else:
                        result.status = ComparisonStatus.ERROR
                    result.error_message = error_msg
                    log(f"  [bold red]Fehlgeschlagen nach {self.MAX_RETRIES} Versuchen: {error_msg}[/bold red]")

    async def _do_capture_page(
        self,
        result: ScreenshotResult,
        output_dir: str,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        """Fuehrt den eigentlichen Screenshot einer Seite durch.

        Args:
            result: ScreenshotResult das befuellt wird.
            output_dir: Verzeichnis fuer den Screenshot.
            log: Logging-Callback fuer Debug-Ausgaben.
        """
        if not self._browser or not self._browser.is_connected():
            raise RuntimeError("Browser nicht verbunden")

        context = await self._browser.new_context(
            ignore_https_errors=True,
            java_script_enabled=True,
            user_agent=self.user_agent,
            viewport={"width": self.viewport_width, "height": self.viewport_height},
        )

        # Custom Cookies setzen (z.B. Auth-Cookies fuer Test-Umgebungen)
        if self.cookies:
            parsed = urlparse(result.url)
            domain = parsed.hostname or ""
            cookie_list = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": "/",
                }
                for c in self.cookies
            ]
            await context.add_cookies(cookie_list)

        page = await context.new_page()

        try:
            page.set_default_timeout(self.timeout * 1000)

            # Seite laden
            start_time = time.monotonic()
            response = await page.goto(
                result.url,
                wait_until="networkidle",
                timeout=self.timeout * 1000,
            )
            elapsed = time.monotonic() - start_time
            result.load_time_ms = int(elapsed * 1000)

            if response:
                result.http_status_code = response.status

            # Consent-Banner automatisch akzeptieren
            await self._accept_consent(page, log)

            # Lazy-Loading triggern: Seite durchscrollen
            await self._trigger_lazy_loading(page, log)

            # Screenshot erstellen
            url_hash = _url_to_hash(result.url)
            screenshot_path = os.path.join(output_dir, f"{url_hash}.png")

            await page.screenshot(
                full_page=self.full_page,
                path=screenshot_path,
                type="png",
            )

            result.screenshot_path = screenshot_path
            # Status wird spaeter vom Comparator gesetzt (MATCH/DIFF/NEW_BASELINE)
            # Hier nur markieren, dass der Screenshot erfolgreich war
            result.status = ComparisonStatus.MATCH

        finally:
            await context.close()

    async def _accept_consent(
        self,
        page: Page,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        """Akzeptiert Cookie-Consent-Banner automatisch.

        Versucht zuerst JavaScript-APIs (Usercentrics, OneTrust, CookieBot),
        dann Fallback auf Button-Klick via CSS-Selektoren, danach Banner
        verstecken.

        Args:
            page: Die Playwright-Page.
            log: Logging-Callback.
        """
        # Phase 1: JavaScript-API aufrufen
        try:
            consent_result = await page.evaluate("""() => {
                // Usercentrics
                if (window.UC_UI && typeof window.UC_UI.acceptAllConsents === 'function') {
                    window.UC_UI.acceptAllConsents();
                    return 'usercentrics';
                }
                // OneTrust
                if (window.OneTrust && typeof window.OneTrust.AllowAll === 'function') {
                    window.OneTrust.AllowAll();
                    return 'onetrust';
                }
                // CookieBot
                if (window.Cookiebot && typeof window.Cookiebot.submitCustomConsent === 'function') {
                    window.Cookiebot.submitCustomConsent(true, true, true);
                    return 'cookiebot';
                }
                return null;
            }""")
            if consent_result:
                log(f"    Consent akzeptiert ({consent_result})")
                await page.wait_for_timeout(2000)
                # Banner verstecken als Sicherheit
                await self._hide_consent_banners(page)
                return
        except Exception:
            pass

        # Phase 2: Fallback - Consent-Buttons per Klick akzeptieren
        consent_selectors = [
            # Usercentrics Buttons
            '[data-testid="uc-accept-all-button"]',
            '#uc-btn-accept-banner',
            '.uc-btn-accept',
            # OneTrust Buttons
            '#onetrust-accept-btn-handler',
            '.onetrust-close-btn-handler',
            # CookieBot Buttons
            '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
            '#CybotCookiebotDialogBodyButtonAccept',
            # Generische Consent-Buttons
            '[data-cookie-accept]',
            '[data-consent-accept]',
            'button[class*="accept"]',
            'button[class*="consent"]',
            'a[class*="accept"]',
            '.cookie-accept',
            '.cookie-consent-accept',
            '#cookie-accept',
            '#accept-cookies',
            '.cc-accept',
            '.cc-btn.cc-allow',
        ]

        clicked = False
        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=500):
                    await button.click(timeout=2000)
                    log(f"    Consent-Button geklickt: {selector}")
                    clicked = True
                    break
            except Exception:
                continue

        if clicked:
            await page.wait_for_timeout(2000)

        # Phase 3: Banner per CSS verstecken (Fallback falls Button-Klick nicht reicht)
        await self._hide_consent_banners(page)

        if not clicked:
            await page.wait_for_timeout(1000)

    async def _hide_consent_banners(self, page: Page) -> None:
        """Versteckt gaengige Consent-Banner per CSS display:none.

        Args:
            page: Die Playwright-Page.
        """
        try:
            await page.evaluate("""() => {
                var selectors = [
                    '#usercentrics-root',
                    '#uc-banner',
                    '.uc-banner',
                    '#onetrust-banner-sdk',
                    '#onetrust-consent-sdk',
                    '#CybotCookiebotDialog',
                    '#CybotCookiebotDialogBodyUnderlay',
                    '.cookie-banner',
                    '.cookie-consent',
                    '.cookie-notice',
                    '[class*="cookie-banner"]',
                    '[class*="cookie-consent"]',
                    '[id*="cookie-banner"]',
                    '[id*="cookie-consent"]',
                    '[class*="consent-banner"]',
                    '[class*="CookieConsent"]',
                ];
                selectors.forEach(function(sel) {
                    try {
                        var els = document.querySelectorAll(sel);
                        els.forEach(function(el) { el.style.display = 'none'; });
                    } catch(e) {}
                });

                // Usercentrics Shadow DOM
                var ucRoot = document.getElementById('usercentrics-root');
                if (ucRoot && ucRoot.shadowRoot) {
                    var shadowBanners = ucRoot.shadowRoot.querySelectorAll('[class*="banner"]');
                    shadowBanners.forEach(function(el) { el.style.display = 'none'; });
                }

                // Body Overflow zuruecksetzen (Consent-Banner blockieren oft Scrollen)
                document.body.style.overflow = '';
                document.documentElement.style.overflow = '';
            }""")
        except Exception:
            pass

    async def _trigger_lazy_loading(
        self,
        page: Page,
        log: Callable[[str], None] = lambda _: None,
    ) -> None:
        """Scrollt die Seite durch, um Lazy-Loading-Bilder zu triggern.

        Scrollt schrittweise nach unten, dann zurueck nach oben, und
        wartet danach auf das Laden aller Bilder.

        Args:
            page: Die Playwright-Page.
            log: Logging-Callback.
        """
        try:
            # Seitenhoehe ermitteln und schrittweise scrollen
            scroll_height = await page.evaluate("() => document.body.scrollHeight")
            viewport_h = self.viewport_height
            scroll_step = viewport_h  # Ein Viewport pro Schritt
            current_pos = 0

            while current_pos < scroll_height:
                current_pos += scroll_step
                await page.evaluate(f"window.scrollTo(0, {current_pos})")
                await page.wait_for_timeout(200)

            # Zurueck nach oben scrollen
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            # Warten bis alle Bilder geladen sind
            loaded = await page.evaluate("""() => {
                return new Promise(function(resolve) {
                    var images = Array.from(document.querySelectorAll('img'));
                    if (images.length === 0) {
                        resolve({total: 0, loaded: 0});
                        return;
                    }

                    var checkCount = 0;
                    var maxChecks = 20;

                    function check() {
                        var loadedCount = images.filter(function(img) {
                            return img.complete && img.naturalWidth > 0;
                        }).length;

                        if (loadedCount >= images.length || checkCount >= maxChecks) {
                            resolve({total: images.length, loaded: loadedCount});
                            return;
                        }

                        checkCount++;
                        setTimeout(check, 250);
                    }
                    check();
                });
            }""")

            if loaded and loaded.get("total", 0) > 0:
                log(f"    Bilder geladen: {loaded['loaded']}/{loaded['total']}")

            # Zusaetzliche Wartezeit damit spaet geladene Bilder fertig rendern
            await page.wait_for_timeout(1000)

        except Exception as e:
            log(f"    Lazy-Loading-Check fehlgeschlagen: {e}")

    async def _launch_browser(self) -> Browser:
        """Startet den Chromium-Browser.

        Returns:
            Playwright Browser-Instanz.
        """
        return await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

    async def _check_network(self) -> bool:
        """Prueft ob das Netzwerk erreichbar ist.

        Returns:
            True wenn Netzwerk verfuegbar.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                response = await client.head("https://www.google.com")
                return response.status_code < 500
        except Exception:
            return False

    async def _wait_for_network(self, max_wait: int = 60) -> None:
        """Wartet bis das Netzwerk wieder verfuegbar ist.

        Args:
            max_wait: Maximale Wartezeit in Sekunden.
        """
        start = time.monotonic()
        while time.monotonic() - start < max_wait:
            if await self._check_network():
                return
            await asyncio.sleep(2)

    def cancel(self) -> None:
        """Bricht den laufenden Scan ab."""
        self._cancelled = True

    async def _cleanup(self) -> None:
        """Rauemt Browser und Playwright auf."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

        self._browser = None
        self._playwright = None


def _url_to_hash(url: str) -> str:
    """Erzeugt einen kurzen Hash aus einer URL fuer den Dateinamen.

    Args:
        url: Die URL.

    Returns:
        Erste 16 Zeichen des SHA256-Hashes.
    """
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
