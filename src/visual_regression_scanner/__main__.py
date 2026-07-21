"""Entry Point fuer Visual Regression Scanner."""

from __future__ import annotations

import argparse
import os
import sys

# Frozen-EXE Erkennung (PyInstaller UND Nuitka):
# PLAYWRIGHT_BROWSERS_PATH muss gesetzt werden BEVOR playwright importiert wird,
# damit das gebundelte Chromium im "browsers"-Unterordner gefunden wird.
# PyInstaller setzt sys.frozen, Nuitka setzt stattdessen __compiled__.
_is_frozen = getattr(sys, "frozen", False) or "__compiled__" in globals()
if _is_frozen:
    _exe_dir = os.path.dirname(sys.executable)
    _browsers_dir = os.path.join(_exe_dir, "browsers")
    if os.path.isdir(_browsers_dir):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _browsers_dir

from textual_widgets import reset_terminal_title, set_terminal_title

from visual_regression_scanner import __version__
from visual_regression_scanner.app import VisualRegressionScannerApp

BANNER = f"""
  Visual Regression Scanner v{__version__}
  Erkennt visuelle Aenderungen auf Websites per Screenshot-Vergleich
"""

USAGE_EXAMPLES = """
Beispiele:
  visual-regression-scanner https://example.com/sitemap.xml
  visual-regression-scanner https://example.com/sitemap.xml --threshold 0.5
  visual-regression-scanner https://example.com/sitemap.xml --viewport 1280x720
  visual-regression-scanner https://example.com/sitemap.xml --output-html report.html
  visual-regression-scanner https://example.com/sitemap.xml --filter /produkte
  visual-regression-scanner https://example.com/sitemap.xml --cookie auth=token123

Tastenkuerzel in der TUI:
  u = URL eingeben    c = Scan starten             s = Einstellungen
  h = Verlauf         r = Reset                    R = Reports
  o = Bilder im Browser                            l = Log ein/aus
  e = Nur Diffs       / = Filter                   + / - = Log-Hoehe
  i = Info            q = Beenden

  Das Log kopieren, exportieren oder ausblenden: Rechtsklick im Log-Bereich.
"""


def _build_parser() -> argparse.ArgumentParser:
    """Baut die Kommandozeilen-Schnittstelle auf.

    Getrennt von main(), damit die Vorgabewerte testbar bleiben und der
    Einstiegspunkt schlank ist.
    """
    parser = argparse.ArgumentParser(
        prog="visual-regression-scanner",
        description=BANNER,
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "sitemap_url",
        nargs="?",
        default="",
        metavar="SITEMAP_URL",
        help="URL der Sitemap (XML)",
    )
    parser.add_argument(
        "--screenshots-dir",
        "-d",
        default="./screenshots",
        metavar="PATH",
        help="Root-Verzeichnis für Screenshots (default: ./screenshots). Pro Site wird ein Unterverzeichnis angelegt.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Diff-Schwelle in Prozent (default: 0.1)",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        default=True,
        help="Full-Page-Screenshot (default: True)",
    )
    parser.add_argument(
        "--no-full-page",
        action="store_true",
        default=False,
        help="Nur sichtbaren Bereich screenshotten",
    )
    parser.add_argument(
        "--viewport",
        default="",
        metavar="WIDTHxHEIGHT",
        help="Viewport-Größe (default: 1920x1080)",
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=None,
        metavar="N",
        help="Max parallele Browser-Tabs (Vorgabe aus den Einstellungen: 4)",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Max. Seiten pro Minute (default: 60). Mit 0 laeuft der Scan ungebremst - "
            "jede Seite wird für den Screenshot voll gerendert und belastet ein "
            "Produktivsystem entsprechend"
        ),
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        default=False,
        help="robots.txt ignorieren (nur für eigene Seiten sinnvoll)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=None,
        metavar="SEC",
        help="Timeout pro Seite in Sekunden (default: 30)",
    )
    parser.add_argument(
        "--output-json",
        default="",
        metavar="PATH",
        help="JSON-Report automatisch speichern",
    )
    parser.add_argument(
        "--output-html",
        default="",
        metavar="PATH",
        help="HTML-Report automatisch speichern",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        default=False,
        help="Browser sichtbar starten (Debugging)",
    )
    parser.add_argument(
        "--filter",
        "-f",
        default="",
        metavar="TEXT",
        help="Nur URLs scannen die TEXT enthalten",
    )
    parser.add_argument(
        "--user-agent",
        default="",
        metavar="UA",
        help="Custom User-Agent String (default: Chrome 131)",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Cookie setzen (z.B. --cookie auth=token). Mehrfach verwendbar.",
    )

    return parser


def main() -> None:
    """Haupteinstiegspunkt fuer die CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    # Ohne Sitemap startet die TUI leer - die URL laesst sich dort mit "u"
    # nachreichen. Das entspricht dem Verhalten der Schwester-Werkzeuge; vorher
    # war das Programm ohne Argument gar nicht benutzbar.

    # Cookies parsen: "NAME=VALUE" -> {"name": "NAME", "value": "VALUE"}
    cookies = []
    for cookie_str in args.cookie:
        if "=" not in cookie_str:
            print(f"Ungültig: --cookie {cookie_str} (Format: NAME=VALUE)")
            sys.exit(1)
        name, value = cookie_str.split("=", 1)
        cookies.append({"name": name.strip(), "value": value.strip()})

    # Full-Page: nur wenn ein Schalter angegeben wurde - sonst None, damit die
    # gespeicherte Einstellung gilt.
    if args.no_full_page:
        full_page = False
    elif args.full_page:
        full_page = True
    else:
        full_page = None

    # Terminal-Tab-Titel setzen - Textual macht das nicht selbst.
    set_terminal_title(f"visual-regression-scanner v{__version__}")
    try:
        app = VisualRegressionScannerApp(
            sitemap_url=args.sitemap_url,
            screenshots_dir=args.screenshots_dir,
            threshold=args.threshold,
            full_page=full_page,
            viewport=args.viewport,
            concurrency=args.concurrency,
            timeout=args.timeout,
            output_json=args.output_json,
            output_html=args.output_html,
            headless=not args.no_headless,
            url_filter=args.filter,
            user_agent=args.user_agent,
            cookies=cookies,
            rate_per_minute=args.rate_limit,
            respect_robots=False if args.ignore_robots else None,
        )
        app.run()
    finally:
        reset_terminal_title()


if __name__ == "__main__":
    main()
