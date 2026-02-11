"""Report-Service - Erzeugt HTML- und JSON-Reports mit eingebetteten Bildern."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path

from ..models.scan_result import ComparisonStatus, ComparisonSummary, ScreenshotResult


class Reporter:
    """Erzeugt Reports aus Vergleichs-Ergebnissen."""

    @staticmethod
    def save_json(
        results: list[ScreenshotResult],
        summary: ComparisonSummary,
        output_path: str,
    ) -> str:
        """Speichert die Ergebnisse als JSON-Report.

        Args:
            results: Liste der Vergleichs-Ergebnisse.
            summary: Gesamtzusammenfassung.
            output_path: Pfad fuer die JSON-Datei.

        Returns:
            Absoluter Pfad der gespeicherten Datei.
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary.to_dict(),
            "results": [r.to_dict() for r in results],
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        return str(path.resolve())

    @staticmethod
    def save_html(
        results: list[ScreenshotResult],
        summary: ComparisonSummary,
        output_path: str,
    ) -> str:
        """Speichert die Ergebnisse als HTML-Report (self-contained mit Base64-Bildern).

        Args:
            results: Liste der Vergleichs-Ergebnisse.
            summary: Gesamtzusammenfassung.
            output_path: Pfad fuer die HTML-Datei.

        Returns:
            Absoluter Pfad der gespeicherten Datei.
        """
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        duration_s = summary.scan_duration_ms / 1000 if summary.scan_duration_ms > 0 else 0

        # Ergebnis-Zeilen aufbauen
        result_rows = []
        for idx, r in enumerate(results, 1):
            status_class = _status_css_class(r.status)
            diff_str = f"{r.diff_percentage:.2f}%" if r.diff_percentage > 0 else "-"
            pixel_str = f"{r.diff_pixel_count:,}" if r.diff_pixel_count > 0 else "-"

            result_rows.append(
                f"<tr class='{status_class}' onclick=\"toggleDetail('detail-{idx}')\">"
                f"<td>{idx}</td>"
                f"<td class='status-cell'>{_html_escape(r.status_icon)}</td>"
                f"<td><a href='{_html_escape(r.url)}' target='_blank'>{_html_escape(r.url)}</a></td>"
                f"<td>{r.http_status_code if r.http_status_code > 0 else '-'}</td>"
                f"<td>{diff_str}</td>"
                f"<td>{pixel_str}</td>"
                f"</tr>"
            )

            # Detail-Row mit Bildern (nur wenn Screenshot vorhanden)
            if r.screenshot_path and os.path.exists(r.screenshot_path):
                images_html = _build_image_row(r)
                error_info = ""
                if r.error_message:
                    error_info = f"<p class='error-msg'>{_html_escape(r.error_message)}</p>"

                result_rows.append(
                    f"<tr class='detail-row' id='detail-{idx}' style='display:none'>"
                    f"<td colspan='6'>"
                    f"{error_info}"
                    f"<div class='image-comparison'>{images_html}</div>"
                    f"</td></tr>"
                )

        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Visual Regression Report - {timestamp}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        h1 {{ color: #58a6ff; margin-bottom: 10px; font-size: 1.5rem; }}
        .timestamp {{ color: #8b949e; margin-bottom: 20px; }}

        .summary {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px; }}
        .summary-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px 20px; min-width: 120px; }}
        .summary-card .label {{ color: #8b949e; font-size: 0.8rem; text-transform: uppercase; }}
        .summary-card .value {{ font-size: 1.8rem; font-weight: bold; margin-top: 5px; }}
        .summary-card .value.ok {{ color: #3fb950; }}
        .summary-card .value.warning {{ color: #d29922; }}
        .summary-card .value.error {{ color: #f85149; }}
        .summary-card .value.info {{ color: #58a6ff; }}

        table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 6px; overflow: hidden; }}
        th {{ background: #21262d; color: #8b949e; text-align: left; padding: 10px 12px; font-size: 0.8rem; text-transform: uppercase; }}
        td {{ padding: 8px 12px; border-top: 1px solid #21262d; font-size: 0.9rem; }}
        tr.match td {{ color: #c9d1d9; }}
        tr.diff td {{ color: #f85149; }}
        tr.new td {{ color: #58a6ff; }}
        tr.error td {{ color: #f85149; }}
        tr.timeout td {{ color: #d29922; }}
        tr[onclick] {{ cursor: pointer; }}
        tr[onclick]:hover {{ background: #1c2128; }}
        tr.detail-row td {{ background: #1c2128; padding: 15px 20px; }}

        .status-cell {{ font-weight: bold; }}
        a {{ color: #58a6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        .image-comparison {{ display: flex; gap: 15px; flex-wrap: wrap; }}
        .image-box {{ flex: 1; min-width: 250px; }}
        .image-box h3 {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 8px; text-transform: uppercase; }}
        .image-box img {{ max-width: 400px; width: 100%; border: 1px solid #30363d; border-radius: 4px; cursor: pointer; }}
        .image-box img:hover {{ border-color: #58a6ff; }}

        .error-msg {{ color: #f85149; margin-bottom: 10px; font-size: 0.85rem; }}

        .footer {{ margin-top: 20px; color: #484f58; font-size: 0.8rem; text-align: center; }}

        /* Fullscreen-Overlay */
        .overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; cursor: pointer; }}
        .overlay img {{ max-width: 95%; max-height: 95%; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }}
    </style>
</head>
<body>
    <h1>Visual Regression Report</h1>
    <p class="timestamp">
        Erstellt: {timestamp} | Sitemap: {_html_escape(summary.sitemap_url)} |
        Threshold: {summary.threshold}% | Viewport: {summary.viewport}
    </p>

    <div class="summary">
        <div class="summary-card">
            <div class="label">URLs gesamt</div>
            <div class="value">{summary.total_urls}</div>
        </div>
        <div class="summary-card">
            <div class="label">OK</div>
            <div class="value ok">{summary.matches}</div>
        </div>
        <div class="summary-card">
            <div class="label">Diffs</div>
            <div class="value {"error" if summary.diffs > 0 else "ok"}">{summary.diffs}</div>
        </div>
        <div class="summary-card">
            <div class="label">Neue</div>
            <div class="value {"info" if summary.new_baselines > 0 else "ok"}">{summary.new_baselines}</div>
        </div>
        <div class="summary-card">
            <div class="label">Fehler</div>
            <div class="value {"error" if summary.errors > 0 else "ok"}">{summary.errors}</div>
        </div>
        <div class="summary-card">
            <div class="label">Timeouts</div>
            <div class="value {"warning" if summary.timeouts > 0 else "ok"}">{summary.timeouts}</div>
        </div>
        <div class="summary-card">
            <div class="label">Dauer</div>
            <div class="value">{duration_s:.1f}s</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Status</th>
                <th>URL</th>
                <th>HTTP</th>
                <th>Diff %</th>
                <th>Pixel</th>
            </tr>
        </thead>
        <tbody>
            {''.join(result_rows)}
        </tbody>
    </table>

    <p class="footer">Visual Regression Scanner v1.0.0 | {timestamp}</p>

    <div class="overlay" id="overlay" onclick="this.style.display='none'">
        <img id="overlay-img" src="" alt="Vollbild">
    </div>

    <script>
        function toggleDetail(id) {{
            var row = document.getElementById(id);
            if (row) {{
                row.style.display = row.style.display === 'none' ? '' : 'none';
            }}
        }}
        function showFullscreen(src) {{
            document.getElementById('overlay-img').src = src;
            document.getElementById('overlay').style.display = 'block';
        }}
    </script>
</body>
</html>"""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

        return str(path.resolve())


def _build_image_row(result: ScreenshotResult) -> str:
    """Erzeugt HTML fuer die Bild-Vergleichsansicht einer URL.

    Args:
        result: Das ScreenshotResult mit Bildpfaden.

    Returns:
        HTML-String mit Base64-eingebetteten Bildern.
    """
    parts = []

    # Baseline
    if result.baseline_path and os.path.exists(result.baseline_path):
        b64 = _image_to_base64(result.baseline_path)
        parts.append(
            f"<div class='image-box'>"
            f"<h3>Baseline</h3>"
            f"<img src='data:image/png;base64,{b64}' alt='Baseline' "
            f"onclick=\"showFullscreen(this.src)\">"
            f"</div>"
        )

    # Aktuell
    if result.screenshot_path and os.path.exists(result.screenshot_path):
        b64 = _image_to_base64(result.screenshot_path)
        parts.append(
            f"<div class='image-box'>"
            f"<h3>Aktuell</h3>"
            f"<img src='data:image/png;base64,{b64}' alt='Aktuell' "
            f"onclick=\"showFullscreen(this.src)\">"
            f"</div>"
        )

    # Diff
    if result.diff_path and os.path.exists(result.diff_path):
        b64 = _image_to_base64(result.diff_path)
        parts.append(
            f"<div class='image-box'>"
            f"<h3>Diff ({result.diff_percentage:.2f}%)</h3>"
            f"<img src='data:image/png;base64,{b64}' alt='Diff' "
            f"onclick=\"showFullscreen(this.src)\">"
            f"</div>"
        )

    return "".join(parts)


def _image_to_base64(image_path: str) -> str:
    """Liest ein Bild und konvertiert es zu Base64.

    Args:
        image_path: Pfad zum Bild.

    Returns:
        Base64-kodierter String.
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _status_css_class(status: ComparisonStatus) -> str:
    """Gibt die CSS-Klasse fuer einen Status zurueck.

    Args:
        status: ComparisonStatus.

    Returns:
        CSS-Klassenname.
    """
    classes = {
        ComparisonStatus.MATCH: "match",
        ComparisonStatus.DIFF: "diff",
        ComparisonStatus.NEW_BASELINE: "new",
        ComparisonStatus.ERROR: "error",
        ComparisonStatus.TIMEOUT: "timeout",
    }
    return classes.get(status, "")


def _html_escape(text: str) -> str:
    """Escaped HTML-Sonderzeichen.

    Args:
        text: Zu escapender Text.

    Returns:
        HTML-sicherer Text.
    """
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
