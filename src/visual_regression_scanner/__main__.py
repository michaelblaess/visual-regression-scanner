"""Entry Point fuer Visual Regression Scanner."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .app import VisualRegressionScannerApp


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
  s = Scan starten    u = Baseline ersetzen         r = Reports speichern
  l = Log ein/aus     e = Nur Diffs                / = Filter
  + / - = Log-Hoehe   i = Info                     q = Beenden
"""


def main() -> None:
    """Haupteinstiegspunkt fuer die CLI."""
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
        "--screenshots-dir", "-d",
        default="./screenshots",
        metavar="PATH",
        help="Root-Verzeichnis fuer Screenshots (default: ./screenshots). Pro Site wird ein Unterverzeichnis angelegt.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
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
        default="1920x1080",
        metavar="WIDTHxHEIGHT",
        help="Viewport-Groesse (default: 1920x1080)",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=4,
        metavar="N",
        help="Max parallele Browser-Tabs (default: 4)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=30,
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
        "--filter", "-f",
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

    args = parser.parse_args()

    if not args.sitemap_url:
        parser.print_help()
        sys.exit(1)

    # Cookies parsen: "NAME=VALUE" -> {"name": "NAME", "value": "VALUE"}
    cookies = []
    for cookie_str in args.cookie:
        if "=" not in cookie_str:
            print(f"Ungueltig: --cookie {cookie_str} (Format: NAME=VALUE)")
            sys.exit(1)
        name, value = cookie_str.split("=", 1)
        cookies.append({"name": name.strip(), "value": value.strip()})

    # Full-Page: --no-full-page ueberschreibt --full-page
    full_page = not args.no_full_page

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
    )
    app.run()


if __name__ == "__main__":
    main()
