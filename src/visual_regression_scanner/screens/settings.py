"""Einstellungs-Dialog.

Erbt vom standardisierten ``BaseSettingsScreen`` (textual-widgets): die Basis
liefert Aussehen, Sprach-Tab und Speichern/Abbrechen; diese Klasse ergaenzt nur
die werkzeugeigenen Registerkarten.
"""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Checkbox, Input, Label, Static, TabPane
from textual_slider import Slider
from textual_widgets import BaseSettingsScreen

from ..i18n import t
from ..models.settings import SETTINGS_FILE


class ScannerSettingsScreen(BaseSettingsScreen):  # type: ignore[misc]
    """Einstellungen: Aufnahme, Netzwerk - plus Sprache und Speicherort von der Basis."""

    DEFAULT_CSS = """
    ScannerSettingsScreen .hint {
        color: $text-muted;
        padding: 0 1;
        margin: 1 0 0 0;
    }
    ScannerSettingsScreen .rate-value {
        padding: 0 1;
    }
    ScannerSettingsScreen .rate-value.off {
        color: $text-disabled;
    }
    ScannerSettingsScreen #set-rate {
        width: 1fr;
        margin: 0 1;
    }
    """

    def app_tabs(self) -> ComposeResult:
        """Registerkarten fuer Aufnahme und Netzwerk."""
        with TabPane(t("settings.tab.capture"), id="settings-tab-capture"), VerticalScroll():
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.threshold"))
                yield Input(
                    value=str(self._settings.get("threshold", 0.1)),
                    placeholder="0.1",
                    id="set-threshold",
                )
            yield Static(t("settings.threshold_hint"), classes="hint")
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.viewport"))
                yield Input(
                    value=str(self._settings.get("viewport", "1920x1080")),
                    placeholder="1920x1080",
                    id="set-viewport",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.full_page"))
                yield Checkbox(
                    t("settings.full_page_check"),
                    value=bool(self._settings.get("full_page", True)),
                    id="set-full-page",
                )
            yield Static(t("settings.full_page_hint"), classes="hint")
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.concurrency"))
                yield Input(
                    value=str(self._settings.get("concurrency", 4)),
                    placeholder="4",
                    id="set-concurrency",
                    type="integer",
                )
            rate_on = bool(self._settings.get("rate_limit_enabled", True))
            rate_value = self._clamp(self._settings.get("rate_per_minute", 60), 60, 10, 240)
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.rate"))
                yield Checkbox(t("settings.rate_check"), value=rate_on, id="set-rate-on")
            yield Static(
                self._rate_label(rate_value),
                id="rate-value",
                classes="rate-value" if rate_on else "rate-value off",
            )
            yield Slider(min=10, max=240, step=10, value=rate_value, id="set-rate", disabled=not rate_on)
            yield Static(t("settings.rate_hint"), classes="hint")
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.timeout"))
                yield Input(
                    value=str(self._settings.get("timeout", 30)),
                    placeholder="30",
                    id="set-timeout",
                    type="integer",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.robots"))
                yield Checkbox(
                    t("settings.robots_check"),
                    value=bool(self._settings.get("respect_robots", True)),
                    id="set-robots",
                )
            yield Static(t("settings.robots_hint"), classes="hint")
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.graphics"))
                yield Checkbox(
                    t("settings.graphics_check"),
                    value=bool(self._settings.get("graphics_preview", False)),
                    id="set-graphics",
                )
            yield Static(t("settings.graphics_hint"), classes="hint")
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.no_headless"))
                yield Checkbox(
                    t("settings.no_headless_check"),
                    value=bool(self._settings.get("no_headless", False)),
                    id="set-no-headless",
                )

        with TabPane(t("settings.tab.network"), id="settings-tab-network"), VerticalScroll():
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.proxy"))
                yield Input(
                    value=str(self._settings.get("proxy_url", "")),
                    placeholder="http://proxy-host:port",
                    id="set-proxy",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.user_agent"))
                yield Input(
                    value=str(self._settings.get("user_agent", "")),
                    placeholder=t("settings.user_agent_placeholder"),
                    id="set-user-agent",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.cookies"))
                yield Input(
                    value=str(self._settings.get("cookies", "")),
                    placeholder=t("settings.cookies_placeholder"),
                    id="set-cookies",
                )
            yield Static(t("settings.cookies_hint"), classes="hint")

    @staticmethod
    def _clamp(value: object, default: int, lo: int, hi: int) -> int:
        """Begrenzt einen gespeicherten Wert auf den Bereich des Reglers."""
        try:
            return max(lo, min(hi, int(str(value))))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _rate_label(per_minute: int) -> str:
        """Uebersetzt die Reglerstellung in Klartext (Zahl + Einordnung)."""
        if per_minute <= 30:
            step = t("settings.rate_step.gentle")
        elif per_minute <= 90:
            step = t("settings.rate_step.recommended")
        elif per_minute <= 150:
            step = t("settings.rate_step.fast")
        else:
            step = t("settings.rate_step.reckless")
        return t("settings.rate_label", per_minute=per_minute, step=step)

    @on(Slider.Changed, "#set-rate")
    def _on_rate_changed(self, event: Slider.Changed) -> None:
        """Haelt die Beschriftung ueber dem Regler am aktuellen Wert."""
        self.query_one("#rate-value", Static).update(self._rate_label(int(event.slider.value)))

    @on(Checkbox.Changed, "#set-rate-on")
    def _on_rate_toggled(self, event: Checkbox.Changed) -> None:
        """Sperrt den Regler, solange nicht gedrosselt wird."""
        enabled = bool(event.value)
        self.query_one("#set-rate", Slider).disabled = not enabled
        self.query_one("#rate-value", Static).set_class(not enabled, "off")

    def collect_app_settings(self, settings: dict[str, object]) -> None:
        """Schreibt die Werte aus den Bedienelementen ins Ergebnis-Dict."""
        settings["threshold"] = self._float("#set-threshold", 0.1)
        settings["viewport"] = self.query_one("#set-viewport", Input).value.strip() or "1920x1080"
        settings["full_page"] = self.query_one("#set-full-page", Checkbox).value
        settings["concurrency"] = self._int("#set-concurrency", 4, minimum=1)
        settings["rate_limit_enabled"] = self.query_one("#set-rate-on", Checkbox).value
        settings["rate_per_minute"] = int(self.query_one("#set-rate", Slider).value)
        settings["timeout"] = self._int("#set-timeout", 30, minimum=5)
        settings["respect_robots"] = self.query_one("#set-robots", Checkbox).value
        settings["no_headless"] = self.query_one("#set-no-headless", Checkbox).value
        settings["graphics_preview"] = self.query_one("#set-graphics", Checkbox).value
        settings["proxy_url"] = self.query_one("#set-proxy", Input).value.strip()
        settings["user_agent"] = self.query_one("#set-user-agent", Input).value.strip()
        settings["cookies"] = self.query_one("#set-cookies", Input).value.strip()

    def storage_paths(self) -> list[tuple[str, Path]]:
        """Liefert die Speicherorte fuer die Registerkarte der Basis."""
        return [
            (t("settings.storage.settings"), SETTINGS_FILE),
            (t("settings.storage.disclaimer"), SETTINGS_FILE.parent / "disclaimer.json"),
        ]

    def _int(self, selector: str, default: int, minimum: int = 1) -> int:
        """Liest eine Ganzzahl aus einem Eingabefeld, mit Untergrenze."""
        try:
            return max(minimum, int(self.query_one(selector, Input).value))
        except (ValueError, TypeError):
            return default

    def _float(self, selector: str, default: float) -> float:
        """Liest eine Kommazahl aus einem Eingabefeld.

        Akzeptiert Komma und Punkt als Trennzeichen - wer die Schwelle mit
        deutscher Tastatur eintippt, schreibt eher "0,5" als "0.5".
        """
        raw = self.query_one(selector, Input).value.strip().replace(",", ".")
        try:
            return max(0.0, float(raw))
        except (ValueError, TypeError):
            return default
