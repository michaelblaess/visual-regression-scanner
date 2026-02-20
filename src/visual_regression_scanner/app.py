"""Hauptanwendung fuer Visual Regression Scanner."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, RichLog

from textual_themes import register_all

from . import __version__, __year__
from .models.scan_result import ComparisonStatus, ComparisonSummary, ScreenshotResult
from .models.sitemap import SitemapParser, SitemapError
from .services.baseline import BaselineManager
from .services.comparator import Comparator
from .services.reporter import Reporter
from .services.screenshotter import Screenshotter
from .widgets.diff_detail_view import DiffDetailView
from .widgets.results_table import ResultsTable
from .widgets.summary_panel import SummaryPanel


# Log-Hoehe: min/max/default (Zeilen)
LOG_HEIGHT_DEFAULT = 15
LOG_HEIGHT_MIN = 5
LOG_HEIGHT_MAX = 35
LOG_HEIGHT_STEP = 3


class VisualRegressionScannerApp(App):
    """TUI-Anwendung zum Erkennen visueller Regressionen auf Websites."""

    CSS_PATH = "app.tcss"
    TITLE = f"Visual Regression Scanner v{__version__} ({__year__})"

    BINDINGS = [
        Binding("q", "quit", "Beenden"),
        Binding("s", "start_scan", "Scan"),
        Binding("r", "reset_site", "Reset"),
        Binding("R", "save_reports", "Report", key_display="R"),
        Binding("l", "toggle_log", "Log"),
        Binding("e", "toggle_diffs", "Nur Diffs"),
        Binding("plus", "log_bigger", "Log +", key_display="+"),
        Binding("minus", "log_smaller", "Log -", key_display="-"),
        Binding("slash", "focus_filter", "Filter", key_display="/"),
        Binding("escape", "unfocus_filter", "Filter leeren", show=False),
        Binding("o", "open_images", "Bilder"),
        Binding("c", "copy_log", "Log kopieren"),
        Binding("i", "show_about", "Info"),
    ]

    def __init__(
        self,
        sitemap_url: str = "",
        screenshots_dir: str = "./screenshots",
        threshold: float = 0.1,
        full_page: bool = True,
        viewport: str = "1920x1080",
        concurrency: int = 4,
        timeout: int = 30,
        output_json: str = "",
        output_html: str = "",
        headless: bool = True,
        url_filter: str = "",
        user_agent: str = "",
        cookies: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__()

        # Retro-Themes registrieren (C64, Amiga, Atari ST, IBM Terminal, NeXTSTEP, BeOS)
        register_all(self)

        self.sitemap_url = sitemap_url
        self.screenshots_dir = os.path.abspath(screenshots_dir)
        self.threshold = threshold
        self.full_page = full_page
        self.viewport = viewport
        self.concurrency = concurrency
        self.timeout = timeout
        self.output_json = output_json
        self.output_html = output_html
        self.headless = headless
        self.url_filter = url_filter
        self.user_agent = user_agent
        self.cookies = cookies or []

        # Viewport parsen
        parts = viewport.split("x")
        self.viewport_width = int(parts[0]) if len(parts) >= 2 else 1920
        self.viewport_height = int(parts[1]) if len(parts) >= 2 else 1080

        # Site-spezifische Verzeichnisse (werden nach Sitemap-Load gesetzt)
        self._site_hostname: str = ""
        self._site_dir: str = ""
        self._baseline_dir: str = ""
        self._current_dir: str = ""
        self._diffs_dir: str = ""

        self._urls: list[str] = []
        self._results: list[ScreenshotResult] = []
        self._screenshotter: Screenshotter | None = None
        self._scan_running: bool = False
        self._scan_start_time: float = 0
        self._log_lines: list[str] = []
        self._log_height: int = LOG_HEIGHT_DEFAULT

        # Restore-Progress (fuer Spinner-Animation)
        self._restore_count: int = 0
        self._restore_total: int = 0
        self._restore_restored: int = 0
        self._restore_timer = None
        self._spinner_idx: int = 0

    def compose(self) -> ComposeResult:
        """Erstellt das UI-Layout."""
        yield Header()
        yield SummaryPanel(id="summary")

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield ResultsTable(id="results-table")
                yield RichLog(id="scan-log", highlight=True, markup=True)

            yield DiffDetailView(id="diff-detail")

        yield Footer()

    def on_mount(self) -> None:
        """Initialisierung nach dem Starten."""
        self._write_log(f"[bold]Visual Regression Scanner v{__version__}[/bold]")
        self._write_log(
            f"Concurrency: {self.concurrency} | Timeout: {self.timeout}s | "
            f"Threshold: {self.threshold}% | Viewport: {self.viewport}"
        )
        self._write_log(f"Screenshots: {self.screenshots_dir}")

        # Focus auf die Tabelle setzen damit Footer-Bindings sofort sichtbar
        try:
            from textual.widgets import DataTable
            table = self.query_one("#results-data", DataTable)
            table.focus()
        except Exception:
            pass

        if self.sitemap_url:
            self._load_sitemap()

    def _get_scan_label(self) -> str:
        """Ermittelt den passenden Scan-Button-Text basierend auf dem Zustand.

        Returns:
            Beschreibungstext fuer den Scan-Button im Footer.
        """
        has_baseline = (
            self._baseline_dir
            and os.path.exists(self._baseline_dir)
            and any(f.endswith(".png") for f in os.listdir(self._baseline_dir))
        ) if self._baseline_dir else False

        has_current = (
            self._current_dir
            and os.path.exists(self._current_dir)
            and any(f.endswith(".png") for f in os.listdir(self._current_dir))
        ) if self._current_dir else False

        if has_baseline and has_current:
            return "Scan (Modus waehlen)"
        elif has_baseline:
            return "Scan (vs. Referenz)"
        else:
            return "Scan (Referenz erstellen)"

    def _update_scan_label(self) -> None:
        """Aktualisiert den Scan-Button-Text im Footer.

        Verwendet set_timer um sicherzustellen dass das Update auf dem
        Event-Loop laeuft (nicht im @work-Kontext).
        """
        self.set_timer(0.1, self._apply_scan_label)

    def _apply_scan_label(self) -> None:
        """Wendet das Scan-Label auf die Bindings an und refreshed den Footer."""
        label = self._get_scan_label()
        self._bindings.key_to_bindings["s"] = [
            Binding("s", "start_scan", label, show=True)
        ]
        try:
            self.screen.refresh_bindings()
        except Exception:
            pass

    @work(exclusive=True)
    async def _load_sitemap(self) -> None:
        """Laedt die Sitemap beim Start (Wrapper fuer @work-Dekorator)."""
        await self._do_load_sitemap()

        # Auto-Scan starten wenn CLI-Reports angefordert (ohne Dialog)
        if self.output_json or self.output_html:
            self._do_start_scan(update_baseline=False)

    async def _do_load_sitemap(self) -> None:
        """Laedt die Sitemap und zeigt die URLs an.

        Kann sowohl vom initialen _load_sitemap als auch vom Reset
        aufgerufen werden.
        """
        self._write_log(f"Lade Sitemap: {self.sitemap_url}")

        try:
            parser = SitemapParser(self.sitemap_url, url_filter=self.url_filter, cookies=self.cookies)
            self._urls = await parser.parse()
        except SitemapError as e:
            self._write_log(f"[red]Sitemap-Fehler: {e}[/red]")
            self.app.push_screen(
                _SitemapErrorScreen(f"Sitemap-Fehler:\n\n{e}")
            )
            return
        except Exception as e:
            self._write_log(f"[red]Unerwarteter Fehler: {e}[/red]")
            self.app.push_screen(
                _SitemapErrorScreen(f"Unerwarteter Fehler:\n\n{e}")
            )
            return

        if not self._urls:
            self._write_log("[yellow]Keine URLs in der Sitemap gefunden.[/yellow]")
            self.notify("Keine URLs gefunden!", severity="warning")
            return

        self._write_log(f"[green]{len(self._urls)} URLs geladen[/green]")

        # Hostname aus erster URL extrahieren fuer Site-Verzeichnis
        self._site_hostname = _extract_hostname(self._urls[0])
        self._site_dir = os.path.join(self.screenshots_dir, self._site_hostname)
        self._baseline_dir = os.path.join(self._site_dir, "baseline")
        self._current_dir = os.path.join(self._site_dir, "current")
        self._diffs_dir = os.path.join(self._site_dir, "diffs")

        self._write_log(f"Site-Verzeichnis: {self._site_dir}")

        # Ergebnisse initialisieren
        self._results = [
            ScreenshotResult(url=url, threshold=self.threshold)
            for url in self._urls
        ]

        # Vorherige Ergebnisse wiederherstellen (in Thread, blockiert nicht die TUI)
        self._write_log("Pruefe vorherige Ergebnisse...")
        self._restore_count = 0
        self._restore_total = len(self._urls)
        self._restore_restored = 0
        self._spinner_idx = 0
        self._restore_timer = self.set_interval(0.1, self._animate_restore_progress)

        restored = await asyncio.to_thread(self._restore_previous_results)

        if self._restore_timer:
            self._restore_timer.stop()
            self._restore_timer = None

        if restored > 0:
            self._write_log(f"[green]{restored} Ergebnisse aus vorherigem Scan wiederhergestellt[/green]")
            # Cache speichern/aktualisieren (falls neu berechnet wurde)
            self._save_results_cache()

        # UI aktualisieren
        summary = self.query_one("#summary", SummaryPanel)
        summary.set_sitemap(self.sitemap_url, len(self._urls))
        if restored > 0:
            summary.update_from_results(self._results)

        table = self.query_one("#results-table", ResultsTable)
        table.load_results(self._results)

        self.sub_title = f"{len(self._urls)} URLs"
        self._update_scan_label()

    # Name der Cache-Datei fuer gespeicherte Vergleichs-Ergebnisse
    RESULTS_CACHE_FILE = "results.json"

    def _save_results_cache(self) -> None:
        """Speichert die aktuellen Ergebnisse als JSON-Cache im Site-Verzeichnis.

        Speichert neben den Ergebnis-Daten auch die Datei-Timestamps
        (mtime) der Bilder, damit der Cache beim naechsten Start
        validiert werden kann.
        """
        if not self._site_dir or not self._results:
            return

        cache_path = os.path.join(self._site_dir, self.RESULTS_CACHE_FILE)

        cache_data = {
            "saved_at": datetime.now().isoformat(),
            "threshold": self.threshold,
            "viewport": self.viewport,
            "sitemap_url": self.sitemap_url,
            "results": [],
        }

        for result in self._results:
            entry = result.to_dict()

            # Datei-Timestamps fuer Validierung speichern
            entry["_baseline_mtime"] = (
                os.path.getmtime(result.baseline_path)
                if result.baseline_path and os.path.exists(result.baseline_path)
                else 0
            )
            entry["_screenshot_mtime"] = (
                os.path.getmtime(result.screenshot_path)
                if result.screenshot_path and os.path.exists(result.screenshot_path)
                else 0
            )
            entry["_diff_mtime"] = (
                os.path.getmtime(result.diff_path)
                if result.diff_path and os.path.exists(result.diff_path)
                else 0
            )

            cache_data["results"].append(entry)

        try:
            os.makedirs(self._site_dir, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_results_cache(self) -> dict | None:
        """Laedt den Ergebnis-Cache aus der JSON-Datei.

        Returns:
            Cache-Dictionary oder None wenn nicht vorhanden/fehlerhaft.
        """
        if not self._site_dir:
            return None

        cache_path = os.path.join(self._site_dir, self.RESULTS_CACHE_FILE)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _animate_restore_progress(self) -> None:
        """Timer-Callback: Aktualisiert den Spinner waehrend der Wiederherstellung."""
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._spinner_idx = (self._spinner_idx + 1) % len(frames)
        spinner = frames[self._spinner_idx]
        text = f"{spinner} Pruefe Ergebnisse... {self._restore_count}/{self._restore_total}"
        if self._restore_restored > 0:
            text += f" ({self._restore_restored} wiederhergestellt)"
        self.sub_title = text

    def _restore_previous_results(self) -> int:
        """Prueft ob Ergebnisse aus einem vorherigen Scan vorhanden sind.

        Versucht zuerst den JSON-Cache zu laden. Fuer jede URL wird geprueft
        ob die Datei-Timestamps noch stimmen. Nur bei Aenderungen wird der
        Diff neu berechnet (Pillow). Dadurch startet die App bei unveraenderten
        Dateien fast sofort.

        Returns:
            Anzahl der wiederhergestellten Ergebnisse.
        """
        if not self._baseline_dir or not self._current_dir:
            return 0

        # Cache laden
        cache = self._load_results_cache()
        cache_by_url: dict[str, dict] = {}
        if cache and cache.get("threshold") == self.threshold:
            for entry in cache.get("results", []):
                url = entry.get("url", "")
                if url:
                    cache_by_url[url] = entry

        comparator: Comparator | None = None  # Lazy init, nur wenn noetig
        restored = 0
        cache_hits = 0
        recalculated = 0

        def log(msg: str) -> None:
            """Thread-sichere Log-Ausgabe."""
            try:
                self.call_from_thread(self._write_log, msg)
            except Exception:
                pass

        for idx, result in enumerate(self._results):
            # Counter aktualisieren (Timer liest diese Werte)
            self._restore_count = idx + 1

            url_hash = hashlib.sha256(result.url.encode("utf-8")).hexdigest()[:16]

            baseline_path = os.path.join(self._baseline_dir, f"{url_hash}.png")
            current_path = os.path.join(self._current_dir, f"{url_hash}.png")
            diff_path = os.path.join(self._diffs_dir, f"{url_hash}.png")

            has_baseline = os.path.exists(baseline_path)
            has_current = os.path.exists(current_path)

            if not has_baseline and not has_current:
                continue

            if has_baseline:
                result.baseline_path = baseline_path

            if has_current:
                result.screenshot_path = current_path

            if has_baseline and has_current:
                # Pruefen ob Cache gueltig ist
                cached = cache_by_url.get(result.url)
                if cached and self._is_cache_valid(cached, baseline_path, current_path, diff_path):
                    # Cache-Hit: Ergebnisse direkt uebernehmen
                    result.status = ComparisonStatus(cached["status"])
                    result.diff_percentage = cached.get("diff_percentage", 0.0)
                    result.diff_pixel_count = cached.get("diff_pixel_count", 0)
                    result.total_pixel_count = cached.get("total_pixel_count", 0)
                    result.http_status_code = cached.get("http_status_code", 0)
                    result.load_time_ms = cached.get("load_time_ms", 0)
                    result.error_message = cached.get("error_message", "")
                    result.retry_count = cached.get("retry_count", 0)
                    result.diff_path = diff_path if os.path.exists(diff_path) else ""
                    restored += 1
                    cache_hits += 1
                    self._restore_restored = restored

                    if result.status == ComparisonStatus.DIFF:
                        log(f"  ({idx + 1}/{len(self._results)}) [red]DIFF {result.diff_percentage:.2f}%[/red] {result.url}")
                    else:
                        log(f"  ({idx + 1}/{len(self._results)}) [green]OK {result.diff_percentage:.2f}%[/green] {result.url}")
                else:
                    # Cache-Miss: Vergleich neu berechnen
                    if comparator is None:
                        comparator = Comparator(threshold=self.threshold)
                    try:
                        diff_pct, diff_px, total_px = comparator.compare(
                            current_path, baseline_path, diff_path,
                        )
                        result.diff_percentage = diff_pct
                        result.diff_pixel_count = diff_px
                        result.total_pixel_count = total_px
                        result.diff_path = diff_path
                        result.status = ComparisonStatus.DIFF if diff_pct > self.threshold else ComparisonStatus.MATCH
                        restored += 1
                        recalculated += 1
                        self._restore_restored = restored

                        if result.status == ComparisonStatus.DIFF:
                            log(f"  ({idx + 1}/{len(self._results)}) [red]DIFF {diff_pct:.2f}%[/red] {result.url} [dim](neu berechnet)[/dim]")
                        else:
                            log(f"  ({idx + 1}/{len(self._results)}) [green]OK {diff_pct:.2f}%[/green] {result.url} [dim](neu berechnet)[/dim]")
                    except Exception as e:
                        log(f"  ({idx + 1}/{len(self._results)}) [red]ERR[/red] {result.url}: {e}")
            elif has_current and not has_baseline:
                # Nur Current vorhanden, keine Baseline
                result.status = ComparisonStatus.NEW_BASELINE
                restored += 1
                self._restore_restored = restored
                log(f"  ({idx + 1}/{len(self._results)}) [blue]NEU[/blue] {result.url}")
            elif has_baseline and not has_current:
                # Nur Baseline vorhanden, kein aktueller Screenshot
                result.status = ComparisonStatus.PENDING

        if cache_hits > 0 or recalculated > 0:
            log(f"  [dim]Cache: {cache_hits} aus Cache, {recalculated} neu berechnet[/dim]")

        return restored

    @staticmethod
    def _is_cache_valid(
        cached: dict,
        baseline_path: str,
        current_path: str,
        diff_path: str,
    ) -> bool:
        """Prueft ob ein Cache-Eintrag noch gueltig ist.

        Vergleicht die gespeicherten Datei-Timestamps mit den aktuellen.
        Der Cache ist ungueltig wenn sich eine Datei geaendert hat.

        Args:
            cached: Cache-Eintrag mit _baseline_mtime, _screenshot_mtime, _diff_mtime.
            baseline_path: Aktueller Pfad zur Baseline.
            current_path: Aktueller Pfad zum Screenshot.
            diff_path: Aktueller Pfad zum Diff-Bild.

        Returns:
            True wenn der Cache noch gueltig ist.
        """
        # Status muss ein auswertbarer Zustand sein
        status = cached.get("status", "")
        if status not in ("match", "diff"):
            return False

        try:
            # Baseline-Timestamp pruefen
            baseline_mtime = os.path.getmtime(baseline_path)
            if abs(baseline_mtime - cached.get("_baseline_mtime", 0)) > 0.01:
                return False

            # Screenshot-Timestamp pruefen
            screenshot_mtime = os.path.getmtime(current_path)
            if abs(screenshot_mtime - cached.get("_screenshot_mtime", 0)) > 0.01:
                return False

            # Diff-Bild muss existieren
            if not os.path.exists(diff_path):
                return False

        except OSError:
            return False

        return True

    def action_start_scan(self) -> None:
        """Startet den Scan - fragt ggf. nach dem Scan-Modus."""
        if self._scan_running:
            self.notify("Scan laeuft bereits!", severity="warning")
            return

        if not self._urls:
            self.notify("Keine URLs geladen! Bitte zuerst eine Sitemap laden.", severity="error")
            return

        # Pruefen ob Referenz UND aktuelle Screenshots vorhanden sind
        baseline_count = 0
        current_count = 0
        if self._baseline_dir and os.path.exists(self._baseline_dir):
            baseline_count = len([f for f in os.listdir(self._baseline_dir) if f.endswith(".png")])
        if self._current_dir and os.path.exists(self._current_dir):
            current_count = len([f for f in os.listdir(self._current_dir) if f.endswith(".png")])

        if baseline_count > 0 and current_count > 0:
            # Beide vorhanden -> Benutzer fragen
            from .screens.scan_mode import ScanModeScreen
            self.push_screen(
                ScanModeScreen(baseline_count, current_count),
                callback=self._on_scan_mode_selected,
            )
        else:
            # Kein Konflikt -> direkt scannen
            self._do_start_scan(update_baseline=False)

    def _on_scan_mode_selected(self, mode: str | None) -> None:
        """Callback nach dem Scan-Modus-Dialog.

        Args:
            mode: 'replace' (nur neue Screenshots), 'update' (Referenz aktualisieren)
                  oder None (abgebrochen).
        """
        if mode is None:
            self.notify("Scan abgebrochen.")
            return

        from .screens.scan_mode import SCAN_UPDATE_BASELINE
        self._do_start_scan(update_baseline=(mode == SCAN_UPDATE_BASELINE))

    @work(exclusive=True)
    async def _do_start_scan(self, update_baseline: bool = False) -> None:
        """Fuehrt den eigentlichen Screenshot-Scan durch.

        Args:
            update_baseline: Wenn True, werden aktuelle Screenshots vorher
                zur neuen Referenz verschoben.
        """
        self._scan_running = True
        self._scan_start_time = time.monotonic()

        # Log einblenden
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.remove_class("hidden")
        log_widget.clear()
        self._log_lines.clear()

        # Option B: Aktuelle Screenshots als neue Referenz uebernehmen
        if update_baseline:
            self._write_log("[bold yellow]Referenz wird aktualisiert...[/bold yellow]")
            await asyncio.to_thread(self._promote_current_to_baseline)

        # Ergebnisse zuruecksetzen (gleiche Objekte behalten!)
        for result in self._results:
            result.status = ComparisonStatus.PENDING
            result.http_status_code = 0
            result.load_time_ms = 0
            result.screenshot_path = ""
            result.baseline_path = ""
            result.diff_path = ""
            result.diff_percentage = 0.0
            result.diff_pixel_count = 0
            result.total_pixel_count = 0
            result.error_message = ""
            result.retry_count = 0

        table = self.query_one("#results-table", ResultsTable)
        table.load_results(self._results)

        # Site-spezifische Verzeichnisse erstellen
        os.makedirs(self._baseline_dir, exist_ok=True)
        os.makedirs(self._current_dir, exist_ok=True)
        os.makedirs(self._diffs_dir, exist_ok=True)

        self._screenshotter = Screenshotter(
            concurrency=self.concurrency,
            timeout=self.timeout,
            headless=self.headless,
            user_agent=self.user_agent,
            cookies=self.cookies,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            full_page=self.full_page,
        )

        def on_result(result: ScreenshotResult) -> None:
            """Callback fuer jedes einzelne Ergebnis."""
            self._on_scan_result(result)

        def on_log(msg: str) -> None:
            """Callback fuer Log-Nachrichten."""
            self._write_log(msg)

        def on_progress(current: int, total: int) -> None:
            """Callback fuer Fortschritt."""
            self._on_scan_progress(current, total)

        try:
            await self._screenshotter.capture_urls(
                self._results,
                output_dir=self._current_dir,
                on_result=on_result,
                on_log=on_log,
                on_progress=on_progress,
            )
        except Exception as e:
            self._write_log(f"[red]Scan-Fehler: {e}[/red]")
            self.notify(f"Scan-Fehler: {e}", severity="error")

        # Screenshots mit Baselines vergleichen
        self._write_log("\n[bold]Vergleiche Screenshots mit Baselines...[/bold]")
        baseline_manager = BaselineManager(self._baseline_dir)
        comparator = Comparator(threshold=self.threshold)

        for result in self._results:
            if result.status not in (ComparisonStatus.MATCH, ComparisonStatus.DIFF, ComparisonStatus.NEW_BASELINE):
                # Nur erfolgreich gescannte Seiten vergleichen
                if result.status in (ComparisonStatus.ERROR, ComparisonStatus.TIMEOUT):
                    continue

            if not result.screenshot_path or not os.path.exists(result.screenshot_path):
                continue

            baseline_path = baseline_manager.get_baseline_path(result.url)

            if not baseline_path:
                # Keine Baseline -> Screenshot wird zur Baseline (nicht in current lassen)
                result.status = ComparisonStatus.NEW_BASELINE
                saved = baseline_manager.save_baseline(result.url, result.screenshot_path)
                result.baseline_path = saved

                # Current-Datei loeschen - beim ersten Scan soll nur die Baseline existieren
                try:
                    os.remove(result.screenshot_path)
                except OSError:
                    pass
                result.screenshot_path = ""

                self._write_log(f"  [blue]NEU[/blue] {result.url} (als Baseline gespeichert)")
            else:
                # Baseline vorhanden -> vergleichen
                result.baseline_path = baseline_path
                diff_path = os.path.join(self._diffs_dir, os.path.basename(result.screenshot_path))

                try:
                    diff_pct, diff_px, total_px = comparator.compare(
                        result.screenshot_path,
                        baseline_path,
                        diff_path,
                    )
                    result.diff_percentage = diff_pct
                    result.diff_pixel_count = diff_px
                    result.total_pixel_count = total_px
                    result.diff_path = diff_path

                    if diff_pct > self.threshold:
                        result.status = ComparisonStatus.DIFF
                        self._write_log(
                            f"  [red]DIFF[/red] {result.url} ({diff_pct:.2f}%)"
                        )
                    else:
                        result.status = ComparisonStatus.MATCH
                        self._write_log(
                            f"  [green]OK[/green] {result.url} ({diff_pct:.2f}%)"
                        )
                except Exception as e:
                    result.status = ComparisonStatus.ERROR
                    result.error_message = str(e)
                    self._write_log(f"  [red]ERR[/red] {result.url}: {e}")

            # Live-Update
            self._on_scan_result(result)

        self._scan_running = False
        self._screenshotter = None

        # Scan abgeschlossen
        duration_ms = int((time.monotonic() - self._scan_start_time) * 1000)
        summary_data = ComparisonSummary.from_results(self.sitemap_url, self._results, duration_ms)
        summary_data.viewport = self.viewport

        self._write_log(f"\n[bold green]Scan abgeschlossen in {duration_ms / 1000:.1f}s[/bold green]")
        self._write_log(
            f"Ergebnis: {summary_data.matches} OK | "
            f"{summary_data.diffs} Diffs | "
            f"{summary_data.new_baselines} Neue | "
            f"{summary_data.errors} Fehler | "
            f"{summary_data.timeouts} Timeouts"
        )

        # Tabelle final aktualisieren
        table = self.query_one("#results-table", ResultsTable)
        table.load_results(self._results)

        # Summary aktualisieren
        summary = self.query_one("#summary", SummaryPanel)
        summary.update_from_results(self._results)

        self.sub_title = f"{len(self._urls)} URLs - Scan abgeschlossen"

        # Ergebnisse als Cache speichern (fuer schnellen Neustart)
        self._save_results_cache()
        self._update_scan_label()

        # Auto-Reports speichern (CLI-Parameter)
        if self.output_json or self.output_html:
            self._save_reports_auto(summary_data)

    def _promote_current_to_baseline(self) -> None:
        """Verschiebt aktuelle Screenshots ins Referenz-Verzeichnis.

        Loescht die alte Referenz, verschiebt current -> baseline,
        und aktualisiert die Metadaten. Laeuft in einem Thread.
        """
        if not self._baseline_dir or not self._current_dir:
            return

        # Alte Referenz loeschen
        if os.path.exists(self._baseline_dir):
            old_count = len([f for f in os.listdir(self._baseline_dir) if f.endswith(".png")])
            shutil.rmtree(self._baseline_dir)
            try:
                self.call_from_thread(
                    self._write_log,
                    f"  Alte Referenz geloescht ({old_count} Bilder)",
                )
            except Exception:
                pass

        os.makedirs(self._baseline_dir, exist_ok=True)

        # Aktuelle Screenshots -> Referenz verschieben
        moved = 0
        if os.path.exists(self._current_dir):
            for filename in os.listdir(self._current_dir):
                if filename.endswith(".png"):
                    src = os.path.join(self._current_dir, filename)
                    dst = os.path.join(self._baseline_dir, filename)
                    shutil.move(src, dst)
                    moved += 1

        try:
            self.call_from_thread(
                self._write_log,
                f"  [green]{moved} Screenshots als neue Referenz gespeichert[/green]",
            )
        except Exception:
            pass

        # Diffs loeschen (sind nicht mehr gueltig)
        if os.path.exists(self._diffs_dir):
            shutil.rmtree(self._diffs_dir)
        os.makedirs(self._diffs_dir, exist_ok=True)

        # Metadata aktualisieren
        baseline_manager = BaselineManager(self._baseline_dir)
        baseline_manager.rebuild_metadata_from_urls(
            [r.url for r in self._results],
            viewport=self.viewport,
        )

    def _on_scan_result(self, result: ScreenshotResult) -> None:
        """Verarbeitet ein einzelnes Scan-Ergebnis (Live-Update).

        Args:
            result: Das aktualisierte ScreenshotResult (gleiches Objekt wie in self._results).
        """
        table = self.query_one("#results-table", ResultsTable)
        table.update_result(result)

        summary = self.query_one("#summary", SummaryPanel)
        summary.update_from_results(self._results)

        # Detail-View aktualisieren falls diese URL gerade angezeigt wird
        detail = self.query_one("#diff-detail", DiffDetailView)
        if detail._result is result:
            detail.refresh_content()

    def _on_scan_progress(self, current: int, total: int) -> None:
        """Aktualisiert den Fortschritt.

        Args:
            current: Aktuell abgeschlossene URLs.
            total: Gesamtanzahl URLs.
        """
        self.sub_title = f"Scanning... {current}/{total}"

    def on_results_table_result_highlighted(
        self, event: ResultsTable.ResultHighlighted
    ) -> None:
        """Aktualisiert die Detail-Ansicht beim Cursor-Wechsel."""
        detail = self.query_one("#diff-detail", DiffDetailView)
        detail.show_result(event.result)

    def on_results_table_result_selected(
        self, event: ResultsTable.ResultSelected
    ) -> None:
        """Oeffnet den Detail-Dialog bei Enter/Doppelklick."""
        from .screens.diff_detail import DiffDetailScreen
        self.push_screen(DiffDetailScreen(event.result))

    def on_diff_detail_view_open_images_requested(
        self, event: DiffDetailView.OpenImagesRequested
    ) -> None:
        """Oeffnet die Bilder im Browser (Button in der Detail-Ansicht)."""
        self._open_images_for_result(event.result)

    def action_save_reports(self) -> None:
        """Speichert HTML- und JSON-Reports."""
        if not self._results:
            self.notify("Keine Ergebnisse vorhanden!", severity="warning")
            return

        scanned = [
            r for r in self._results
            if r.status not in (ComparisonStatus.PENDING, ComparisonStatus.SCANNING)
        ]
        if not scanned:
            self.notify("Noch keine Seiten gescannt!", severity="warning")
            return

        duration_ms = int((time.monotonic() - self._scan_start_time) * 1000) if self._scan_start_time > 0 else 0
        summary = ComparisonSummary.from_results(self.sitemap_url, self._results, duration_ms)
        summary.viewport = self.viewport

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = f"visual-regression-report_{timestamp}.json"
        saved_json = Reporter.save_json(self._results, summary, json_path)
        self._write_log(f"[green]JSON-Report: {saved_json}[/green]")

        # HTML
        html_path = f"visual-regression-report_{timestamp}.html"
        saved_html = Reporter.save_html(self._results, summary, html_path)
        self._write_log(f"[green]HTML-Report: {saved_html}[/green]")

        self.notify(f"Reports gespeichert: {json_path}, {html_path}")

    def _save_reports_auto(self, summary: ComparisonSummary) -> None:
        """Speichert Reports automatisch (CLI-Parameter).

        Args:
            summary: Vergleichs-Zusammenfassung.
        """
        if self.output_json:
            path = Reporter.save_json(self._results, summary, self.output_json)
            self._write_log(f"[green]JSON-Report: {path}[/green]")

        if self.output_html:
            path = Reporter.save_html(self._results, summary, self.output_html)
            self._write_log(f"[green]HTML-Report: {path}[/green]")

    def action_reset_site(self) -> None:
        """Zeigt den Bestaetigungsdialog fuer den Reset an."""
        if self._scan_running:
            self.notify("Scan laeuft! Bitte zuerst abwarten.", severity="warning")
            return

        if not self._site_dir:
            self.notify("Keine Site geladen!", severity="warning")
            return

        # Anzahl vorhandener Dateien zaehlen fuer die Warnung
        file_count = 0
        for sub_dir in (self._baseline_dir, self._current_dir, self._diffs_dir):
            if sub_dir and os.path.exists(sub_dir):
                file_count += len(os.listdir(sub_dir))

        from .screens.reset_confirm import ResetConfirmScreen
        self.push_screen(
            ResetConfirmScreen(self._site_hostname, file_count),
            callback=self._on_reset_confirmed,
        )

    def _on_reset_confirmed(self, confirmed: bool) -> None:
        """Callback nach dem Bestaetigungsdialog.

        Args:
            confirmed: True wenn der Benutzer bestaetigt hat.
        """
        if confirmed:
            self._do_reset_site()

    @work(exclusive=True)
    async def _do_reset_site(self) -> None:
        """Fuehrt den Reset durch: loescht Bilder und laedt Sitemap neu."""
        # Verzeichnisse loeschen (baseline, current, diffs)
        deleted_files = 0
        for sub_dir in (self._baseline_dir, self._current_dir, self._diffs_dir):
            if sub_dir and os.path.exists(sub_dir):
                try:
                    count = len(os.listdir(sub_dir))
                    shutil.rmtree(sub_dir)
                    deleted_files += count
                    self._write_log(f"  Geloescht: {sub_dir} ({count} Dateien)")
                except Exception as e:
                    self._write_log(f"  [red]Fehler beim Loeschen von {sub_dir}: {e}[/red]")

        # Cache-Datei loeschen
        cache_path = os.path.join(self._site_dir, self.RESULTS_CACHE_FILE)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                deleted_files += 1
            except Exception:
                pass

        self._write_log(
            f"[yellow]Reset: {deleted_files} Dateien geloescht fuer {self._site_hostname}[/yellow]"
        )

        # Ergebnisse zuruecksetzen
        self._results.clear()
        self._urls.clear()

        # UI zuruecksetzen
        table = self.query_one("#results-table", ResultsTable)
        table.load_results([])

        summary = self.query_one("#summary", SummaryPanel)
        summary.set_sitemap(self.sitemap_url, 0)

        detail = self.query_one("#diff-detail", DiffDetailView)
        detail.clear()

        # Log leeren
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.clear()
        self._log_lines.clear()

        self._write_log(f"[bold]Reset abgeschlossen. Lade Sitemap neu...[/bold]")
        self.notify(f"Reset: {deleted_files} Dateien geloescht")

        # Sitemap neu laden
        if self.sitemap_url:
            await self._do_load_sitemap()

    def action_open_images(self) -> None:
        """Oeffnet die Bilder der ausgewaehlten URL im Browser (Taste o)."""
        table = self.query_one("#results-table", ResultsTable)
        result = table.get_selected_result()

        if not result:
            self.notify("Keine URL ausgewaehlt!", severity="warning")
            return

        self._open_images_for_result(result)

    def _open_images_for_result(self, result: ScreenshotResult) -> None:
        """Oeffnet die Bilder eines Ergebnisses im Browser.

        Args:
            result: Das ScreenshotResult dessen Bilder geoeffnet werden sollen.
        """
        if not result.screenshot_path:
            self.notify("Kein Screenshot vorhanden! Bitte zuerst scannen.", severity="warning")
            return

        from .services.image_viewer import open_comparison_view
        path = open_comparison_view(result)

        if path:
            self._write_log(f"Bilder geoeffnet: {result.url}")
        else:
            self.notify("Keine Bilder verfuegbar!", severity="warning")

    def action_copy_log(self) -> None:
        """Kopiert das Log in die Zwischenablage."""
        if not self._log_lines:
            self.notify("Log ist leer.", severity="warning")
            return

        text = "\n".join(self._log_lines)
        self.copy_to_clipboard(text)
        self.notify(f"Log kopiert ({len(self._log_lines)} Zeilen)")

    def action_toggle_log(self) -> None:
        """Blendet den Log-Bereich ein/aus."""
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.toggle_class("hidden")

    def action_log_bigger(self) -> None:
        """Vergroessert den Log-Bereich."""
        self._log_height = min(self._log_height + LOG_HEIGHT_STEP, LOG_HEIGHT_MAX)
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.styles.height = self._log_height

    def action_log_smaller(self) -> None:
        """Verkleinert den Log-Bereich."""
        self._log_height = max(self._log_height - LOG_HEIGHT_STEP, LOG_HEIGHT_MIN)
        log_widget = self.query_one("#scan-log", RichLog)
        log_widget.styles.height = self._log_height

    def action_toggle_diffs(self) -> None:
        """Wechselt zwischen alle/nur Diffs in der Tabelle."""
        table = self.query_one("#results-table", ResultsTable)
        table.toggle_diff_filter()

    def action_focus_filter(self) -> None:
        """Fokussiert das Filter-Eingabefeld."""
        try:
            from textual.widgets import Input
            filter_input = self.query_one("#filter-bar", Input)
            filter_input.focus()
        except Exception:
            pass

    def action_unfocus_filter(self) -> None:
        """Leert den Filter und gibt Focus zurueck an die Tabelle."""
        try:
            from textual.widgets import Input, DataTable
            filter_input = self.query_one("#filter-bar", Input)
            filter_input.value = ""
            table = self.query_one("#results-data", DataTable)
            table.focus()
        except Exception:
            pass

    def action_show_about(self) -> None:
        """Zeigt den About-Dialog an."""
        from .screens.about import AboutScreen
        self.push_screen(AboutScreen())

    def _write_log(self, line: str) -> None:
        """Schreibt eine Zeile ins Log-Widget und in den Puffer.

        Args:
            line: Log-Nachricht (kann Rich-Markup enthalten).
        """
        self._log_lines.append(line)
        try:
            self.query_one("#scan-log", RichLog).write(line)
        except Exception:
            pass


def _extract_hostname(url: str) -> str:
    """Extrahiert den Hostnamen aus einer URL fuer das Site-Verzeichnis.

    Args:
        url: Eine beliebige URL aus der Sitemap.

    Returns:
        Hostname (z.B. 'www.example.com').
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or "unknown"
    # Sonderzeichen entfernen die in Verzeichnisnamen problematisch sind
    return hostname.replace(":", "_").replace("/", "_")


class _SitemapErrorScreen(ModalScreen):
    """Modal-Dialog fuer Sitemap-Fehler."""

    DEFAULT_CSS = """
    _SitemapErrorScreen {
        align: center middle;
    }

    _SitemapErrorScreen > Vertical {
        width: 70;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }

    _SitemapErrorScreen #error-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $error;
        color: $text;
        margin-bottom: 1;
    }

    _SitemapErrorScreen #error-message {
        height: auto;
        padding: 1;
    }

    _SitemapErrorScreen #error-footer {
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

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        """Erstellt das Modal-Layout."""
        from textual.containers import Vertical
        from textual.widgets import Static

        with Vertical():
            yield Static("Fehler", id="error-title")
            yield Static(self._message, id="error-message")
            yield Static("ESC = Schliessen", id="error-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
