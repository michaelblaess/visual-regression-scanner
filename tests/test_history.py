"""Tests fuer den Verlauf der geprueften Sitemaps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_regression_scanner.models import history as history_module
from visual_regression_scanner.models.history import MAX_ENTRIES, History, HistoryEntry


@pytest.fixture(autouse=True)
def _temp_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Legt den Verlauf in ein temporaeres Verzeichnis."""
    path = tmp_path / "history.json"
    monkeypatch.setattr(history_module, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(history_module, "HISTORY_FILE", path)
    return path


class TestStorage:
    def test_empty_without_file(self) -> None:
        assert History.load() == []

    def test_add_and_load(self) -> None:
        History.add(HistoryEntry(url="https://example.com/sitemap.xml"))
        entries = History.load()
        assert len(entries) == 1
        assert entries[0].url == "https://example.com/sitemap.xml"

    def test_timestamp_is_set_automatically(self) -> None:
        History.add(HistoryEntry(url="https://example.com/sitemap.xml"))
        assert History.load()[0].timestamp

    def test_newest_entry_comes_first(self) -> None:
        History.add(HistoryEntry(url="https://a.example/sitemap.xml"))
        History.add(HistoryEntry(url="https://b.example/sitemap.xml"))
        assert History.load()[0].url == "https://b.example/sitemap.xml"

    def test_same_url_is_not_duplicated(self) -> None:
        """Ein wiederholt geprueftes Ziel darf die Liste nicht fuellen."""
        for _ in range(3):
            History.add(HistoryEntry(url="https://example.com/sitemap.xml"))
        assert len(History.load()) == 1

    def test_list_is_capped(self) -> None:
        for i in range(MAX_ENTRIES + 10):
            History.add(HistoryEntry(url=f"https://example.com/{i}.xml"))
        assert len(History.load()) == MAX_ENTRIES

    def test_broken_file_gives_empty_list(self, _temp_history: Path) -> None:
        _temp_history.write_text("kein JSON", encoding="utf-8")
        assert History.load() == []

    def test_garbage_values_fall_back(self, _temp_history: Path) -> None:
        """Ein von Hand bearbeiteter Verlauf darf den Start nicht verhindern."""
        _temp_history.write_text(
            json.dumps([{"url": "https://example.com", "threshold": "viel", "total_pages": None}]),
            encoding="utf-8",
        )
        entry = History.load()[0]
        assert entry.threshold == 0.1
        assert entry.total_pages == 0


class TestStatsUpdate:
    def test_results_are_written_back(self) -> None:
        url = "https://example.com/sitemap.xml"
        History.add(HistoryEntry(url=url))
        History.update_latest_stats(url, pages=42, changed=3, failed=1)

        entry = History.load()[0]
        assert (entry.total_pages, entry.total_changed, entry.total_failed) == (42, 3, 1)

    def test_unknown_url_changes_nothing(self) -> None:
        History.add(HistoryEntry(url="https://a.example/sitemap.xml"))
        History.update_latest_stats("https://andere.example", pages=9, changed=9, failed=9)
        assert History.load()[0].total_pages == 0


class TestDisplay:
    def test_time_is_german_format(self) -> None:
        entry = HistoryEntry(url="x", timestamp="2026-07-21T16:05:00")
        assert entry.display_time == "21.07.2026 16:05"

    def test_missing_time(self) -> None:
        assert HistoryEntry(url="x").display_time == "?"

    def test_result_without_run(self) -> None:
        assert HistoryEntry(url="x").display_result == "-"

    def test_result_mentions_changes_and_failures(self) -> None:
        entry = HistoryEntry(url="x", total_pages=10, total_changed=2, total_failed=1)
        text = entry.display_result
        assert "10 Seiten" in text
        assert "2 geändert" in text
        assert "1 Fehler" in text

    def test_result_hides_zero_counts(self) -> None:
        entry = HistoryEntry(url="x", total_pages=10)
        assert entry.display_result == "10 Seiten"
