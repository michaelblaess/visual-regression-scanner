"""Baseline-Service - Verwaltet Baseline-Screenshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..i18n import t

if TYPE_CHECKING:
    from ..models.scan_result import ScreenshotResult


class BaselineManager:
    """Verwaltet Baseline-Screenshots fuer den Vergleich."""

    METADATA_FILE = "metadata.json"

    def __init__(self, baseline_dir: str) -> None:
        self.baseline_dir = baseline_dir
        os.makedirs(baseline_dir, exist_ok=True)

    def get_baseline_path(self, url: str) -> str | None:
        """Gibt den Pfad zur Baseline fuer eine URL zurueck.

        Args:
            url: Die URL.

        Returns:
            Pfad zur Baseline oder None wenn nicht vorhanden.
        """
        url_hash = self._url_to_hash(url)
        path = os.path.join(self.baseline_dir, f"{url_hash}.png")
        if os.path.exists(path):
            return path
        return None

    def save_baseline(self, url: str, screenshot_path: str) -> str:
        """Speichert einen Screenshot als Baseline.

        Args:
            url: Die URL des Screenshots.
            screenshot_path: Pfad zum aktuellen Screenshot.

        Returns:
            Pfad der gespeicherten Baseline.
        """
        url_hash = self._url_to_hash(url)
        baseline_path = os.path.join(self.baseline_dir, f"{url_hash}.png")

        shutil.copy2(screenshot_path, baseline_path)

        # Metadata aktualisieren
        metadata = self.get_metadata()
        if "urls" not in metadata:
            metadata["urls"] = {}

        metadata["urls"][url] = {
            "filename": f"{url_hash}.png",
            "last_updated": datetime.now().isoformat(),
        }

        self.save_metadata(metadata)

        return baseline_path

    def has_baseline(self, url: str) -> bool:
        """Prueft ob eine Baseline fuer die URL existiert.

        Args:
            url: Die URL.

        Returns:
            True wenn eine Baseline existiert.
        """
        return self.get_baseline_path(url) is not None

    def get_metadata(self) -> dict[str, Any]:
        """Laedt die Metadata-Datei.

        Returns:
            Dictionary mit Metadata oder leeres Dict.
        """
        metadata_path = os.path.join(self.baseline_dir, self.METADATA_FILE)
        if not os.path.exists(metadata_path):
            return {
                "created": datetime.now().isoformat(),
                "viewport": "",
                "urls": {},
            }

        try:
            with open(metadata_path, encoding="utf-8") as f:
                loaded: dict[str, Any] = json.load(f)
                return loaded
        except (json.JSONDecodeError, OSError):
            return {
                "created": datetime.now().isoformat(),
                "viewport": "",
                "urls": {},
            }

    def save_metadata(self, metadata: dict[str, Any]) -> None:
        """Speichert die Metadata-Datei.

        Args:
            metadata: Dictionary mit Metadata.
        """
        metadata_path = os.path.join(self.baseline_dir, self.METADATA_FILE)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def update_all_baselines(
        self,
        results: list[ScreenshotResult],
        viewport: str = "",
        on_log: Callable[[str], None] | None = None,
    ) -> int:
        """Aktualisiert alle Baselines aus den aktuellen Screenshots.

        Args:
            results: Liste der ScreenshotResults mit screenshot_path.
            viewport: Viewport-Groesse als String.
            on_log: Optionaler Logging-Callback.

        Returns:
            Anzahl der aktualisierten Baselines.
        """
        count = 0

        for result in results:
            if not result.screenshot_path or not os.path.exists(result.screenshot_path):
                continue

            self.save_baseline(result.url, result.screenshot_path)
            count += 1

            if on_log:
                on_log(t("baseline.updated", url=result.url))

        # Viewport in Metadata speichern
        if viewport:
            metadata = self.get_metadata()
            metadata["viewport"] = viewport
            self.save_metadata(metadata)

        return count

    def rebuild_metadata_from_urls(
        self,
        urls: list[str],
        viewport: str = "",
    ) -> None:
        """Erstellt die Metadata-Datei neu basierend auf vorhandenen Dateien.

        Wird nach dem Verschieben von current -> baseline verwendet,
        um die Metadata-Datei korrekt zu rekonstruieren.

        Args:
            urls: Liste aller URLs aus der Sitemap.
            viewport: Viewport-Groesse als String.
        """
        metadata = {
            "created": datetime.now().isoformat(),
            "viewport": viewport,
            "urls": {},
        }

        for url in urls:
            url_hash = self._url_to_hash(url)
            baseline_path = os.path.join(self.baseline_dir, f"{url_hash}.png")
            if os.path.exists(baseline_path):
                raw_urls = metadata.get("urls")
                urls_entry: dict[str, Any] = raw_urls if isinstance(raw_urls, dict) else {}
                metadata["urls"] = urls_entry
                urls_entry[url] = {
                    "filename": f"{url_hash}.png",
                    "last_updated": datetime.now().isoformat(),
                }

        self.save_metadata(metadata)

    def _url_to_hash(self, url: str) -> str:
        """Erzeugt einen kurzen Hash aus einer URL.

        Args:
            url: Die URL.

        Returns:
            Erste 16 Zeichen des SHA256-Hashes.
        """
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
