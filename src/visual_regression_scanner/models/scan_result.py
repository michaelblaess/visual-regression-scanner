"""Datenmodelle fuer Visual Regression Scanner."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComparisonStatus(Enum):
    """Status eines Screenshot-Vergleichs."""

    PENDING = "pending"
    SCANNING = "scanning"
    MATCH = "match"
    DIFF = "diff"
    NEW_BASELINE = "new_baseline"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ScreenshotResult:
    """Ergebnis des Screenshot-Vergleichs einer einzelnen Seite."""

    url: str
    status: ComparisonStatus = ComparisonStatus.PENDING
    http_status_code: int = 0
    load_time_ms: int = 0
    screenshot_path: str = ""
    baseline_path: str = ""
    diff_path: str = ""
    diff_percentage: float = 0.0
    diff_pixel_count: int = 0
    total_pixel_count: int = 0
    threshold: float = 0.1
    error_message: str = ""
    retry_count: int = 0

    @property
    def is_diff(self) -> bool:
        """Hat die Seite einen visuellen Unterschied ueber dem Threshold?"""
        return self.diff_percentage > self.threshold

    @property
    def is_new(self) -> bool:
        """Ist dies eine neue Baseline (keine vorherige Baseline vorhanden)?"""
        return self.status == ComparisonStatus.NEW_BASELINE

    @property
    def has_baseline(self) -> bool:
        """Existiert eine Baseline fuer diese URL?"""
        return self.baseline_path != ""

    @property
    def status_icon(self) -> str:
        """Icon fuer den aktuellen Status."""
        icons = {
            ComparisonStatus.PENDING: "...",
            ComparisonStatus.SCANNING: ">>>",
            ComparisonStatus.MATCH: "OK",
            ComparisonStatus.DIFF: "DIFF",
            ComparisonStatus.NEW_BASELINE: "NEU",
            ComparisonStatus.ERROR: "ERR",
            ComparisonStatus.TIMEOUT: "T/O",
        }
        return icons.get(self.status, "?")

    def to_dict(self) -> dict:
        """Konvertiert das Ergebnis in ein Dictionary."""
        return {
            "url": self.url,
            "status": self.status.value,
            "http_status_code": self.http_status_code,
            "load_time_ms": self.load_time_ms,
            "screenshot_path": self.screenshot_path,
            "baseline_path": self.baseline_path,
            "diff_path": self.diff_path,
            "diff_percentage": round(self.diff_percentage, 4),
            "diff_pixel_count": self.diff_pixel_count,
            "total_pixel_count": self.total_pixel_count,
            "threshold": self.threshold,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScreenshotResult:
        """Erstellt ein ScreenshotResult aus einem Dictionary.

        Args:
            data: Dictionary mit den Ergebnis-Daten (z.B. aus JSON-Cache).

        Returns:
            ScreenshotResult mit den geladenen Werten.
        """
        status_str = data.get("status", "pending")
        try:
            status = ComparisonStatus(status_str)
        except ValueError:
            status = ComparisonStatus.PENDING

        return cls(
            url=data.get("url", ""),
            status=status,
            http_status_code=data.get("http_status_code", 0),
            load_time_ms=data.get("load_time_ms", 0),
            screenshot_path=data.get("screenshot_path", ""),
            baseline_path=data.get("baseline_path", ""),
            diff_path=data.get("diff_path", ""),
            diff_percentage=data.get("diff_percentage", 0.0),
            diff_pixel_count=data.get("diff_pixel_count", 0),
            total_pixel_count=data.get("total_pixel_count", 0),
            threshold=data.get("threshold", 0.1),
            error_message=data.get("error_message", ""),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class ComparisonSummary:
    """Gesamtzusammenfassung eines Vergleichs."""

    sitemap_url: str = ""
    total_urls: int = 0
    scanned_urls: int = 0
    matches: int = 0
    diffs: int = 0
    new_baselines: int = 0
    errors: int = 0
    timeouts: int = 0
    scan_duration_ms: int = 0
    threshold: float = 0.1
    viewport: str = "1920x1080"

    @staticmethod
    def from_results(
        sitemap_url: str,
        results: list[ScreenshotResult],
        duration_ms: int = 0,
    ) -> ComparisonSummary:
        """Erstellt eine Zusammenfassung aus den Scan-Ergebnissen.

        Args:
            sitemap_url: URL der gescannten Sitemap.
            results: Liste der Screenshot-Ergebnisse.
            duration_ms: Scan-Dauer in Millisekunden.

        Returns:
            ComparisonSummary mit aggregierten Werten.
        """
        summary = ComparisonSummary(sitemap_url=sitemap_url)
        summary.total_urls = len(results)
        summary.scan_duration_ms = duration_ms

        for result in results:
            if result.status == ComparisonStatus.MATCH:
                summary.scanned_urls += 1
                summary.matches += 1
            elif result.status == ComparisonStatus.DIFF:
                summary.scanned_urls += 1
                summary.diffs += 1
            elif result.status == ComparisonStatus.NEW_BASELINE:
                summary.scanned_urls += 1
                summary.new_baselines += 1
            elif result.status == ComparisonStatus.ERROR:
                summary.scanned_urls += 1
                summary.errors += 1
            elif result.status == ComparisonStatus.TIMEOUT:
                summary.scanned_urls += 1
                summary.timeouts += 1

        if results:
            summary.threshold = results[0].threshold

        return summary

    def to_dict(self) -> dict:
        """Konvertiert die Zusammenfassung in ein Dictionary."""
        return {
            "sitemap_url": self.sitemap_url,
            "total_urls": self.total_urls,
            "scanned_urls": self.scanned_urls,
            "matches": self.matches,
            "diffs": self.diffs,
            "new_baselines": self.new_baselines,
            "errors": self.errors,
            "timeouts": self.timeouts,
            "scan_duration_ms": self.scan_duration_ms,
            "threshold": self.threshold,
            "viewport": self.viewport,
        }
