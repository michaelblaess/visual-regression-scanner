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
from visual_regression_scanner.i18n import load_locale, t
from visual_regression_scanner.models.settings import Settings


def _build_parser() -> argparse.ArgumentParser:
    """Baut die Kommandozeilen-Schnittstelle auf.

    Getrennt von main(), damit die Vorgabewerte testbar bleiben und der
    Einstiegspunkt schlank ist.
    """
    parser = argparse.ArgumentParser(
        prog="visual-regression-scanner",
        description=f"\n  Visual Regression Scanner v{__version__}\n  {t('cli.description')}\n",
        epilog=t("cli.examples"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "sitemap_url",
        nargs="?",
        default="",
        metavar="SITEMAP_URL",
        help=t("cli.help.sitemap_url"),
    )
    parser.add_argument(
        "--screenshots-dir",
        "-d",
        default="./screenshots",
        metavar="PATH",
        help=t("cli.help.screenshots_dir"),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="FLOAT",
        help=t("cli.help.threshold"),
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        default=True,
        help=t("cli.help.full_page"),
    )
    parser.add_argument(
        "--no-full-page",
        action="store_true",
        default=False,
        help=t("cli.help.no_full_page"),
    )
    parser.add_argument(
        "--viewport",
        default="",
        metavar="WIDTHxHEIGHT",
        help=t("cli.help.viewport"),
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=None,
        metavar="N",
        help=t("cli.help.concurrency"),
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=None,
        metavar="N",
        help=t("cli.help.rate_limit"),
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        default=False,
        help=t("cli.help.ignore_robots"),
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=None,
        metavar="SEC",
        help=t("cli.help.timeout"),
    )
    parser.add_argument(
        "--output-json",
        default="",
        metavar="PATH",
        help=t("cli.help.output_json"),
    )
    parser.add_argument(
        "--output-html",
        default="",
        metavar="PATH",
        help=t("cli.help.output_html"),
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        default=False,
        help=t("cli.help.no_headless"),
    )
    parser.add_argument(
        "--filter",
        "-f",
        default="",
        metavar="TEXT",
        help=t("cli.help.filter"),
    )
    parser.add_argument(
        "--user-agent",
        default="",
        metavar="UA",
        help=t("cli.help.user_agent"),
    )
    parser.add_argument(
        "--cookie",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help=t("cli.help.cookie"),
    )

    return parser


def main() -> None:
    """Haupteinstiegspunkt fuer die CLI."""
    # Die Sprache steht in den Einstellungen und muss vor dem Aufbau der
    # Kommandozeilen-Hilfe geladen sein - deren Texte entstehen sofort.
    load_locale(Settings.load().language)

    parser = _build_parser()
    args = parser.parse_args()

    # Ohne Sitemap startet die TUI leer - die URL laesst sich dort mit "u"
    # nachreichen. Das entspricht dem Verhalten der Schwester-Werkzeuge; vorher
    # war das Programm ohne Argument gar nicht benutzbar.

    # Cookies parsen: "NAME=VALUE" -> {"name": "NAME", "value": "VALUE"}
    cookies = []
    for cookie_str in args.cookie:
        if "=" not in cookie_str:
            print(t("cli.cookie_invalid", value=cookie_str))
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
