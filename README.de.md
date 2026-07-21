# Visual Regression Scanner

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <a href="README.md">English</a> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <b>Deutsch</b>
</p>

<p align="center">
  <a href="https://michaelblaess.github.io/visual-regression-scanner/">Projektseite</a>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/visual-regression-scanner/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/visual-regression-scanner/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/visual-regression-scanner/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/visual-regression-scanner/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/visual-regression-scanner?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/visual-regression-scanner/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

TUI-Tool zur Erkennung visueller Regressionen auf Websites. Erstellt automatisch Full-Page-Screenshots aller Seiten einer Sitemap und vergleicht sie gegen gespeicherte Referenzen per Pixel-Diff.

## Installation

### One-Liner (Standalone, kein Python noetig)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/visual-regression-scanner/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/visual-regression-scanner/main/install.ps1 | iex
```

## Features

- **Automatische Screenshots** aller URLs aus einer XML-Sitemap
- **Pixel-Diff-Vergleich** gegen gespeicherte Referenzen (Baselines)
- **Konfigurierbare Schwelle** (Threshold) für erlaubte Abweichungen
- **TUI** mit Live-Updates, Filter, Detail-Ansicht
- **Dynamischer Scan-Button** - zeigt den aktuellen Zustand im Footer
- **Ergebnis-Cache** (`results.json`) - vermeidet Neuberechnung beim Start
- **HTML-Reports** mit eingebetteten Before/After/Diff-Bildern (Base64)
- **JSON-Reports** für CI/CD-Integration
- **Consent-Handling** (Usercentrics, OneTrust, CookieBot)
- **Lazy-Loading-Erkennung** - scrollt Seiten durch und wartet auf Bilder
- **Parallele Verarbeitung** mit konfigurierbarer Concurrency

## Setup

```bash
# Windows
.\bootstrap.ps1

# Linux/macOS
./bootstrap.sh
```

Das Bootstrap-Skript erstellt eine virtuelle Umgebung, installiert alle Abhängigkeiten und lädt Chromium herunter.

## Verwendung

```bash
# TUI starten
visual-regression-scanner https://example.com/sitemap.xml

# Mit erhoehter Toleranz
visual-regression-scanner https://example.com/sitemap.xml --threshold 0.5

# Kleinerer Viewport
visual-regression-scanner https://example.com/sitemap.xml --viewport 1280x720

# HTML-Report automatisch speichern
visual-regression-scanner https://example.com/sitemap.xml --output-html report.html

# Nur bestimmte URLs
visual-regression-scanner https://example.com/sitemap.xml --filter /produkte

# Mit Auth-Cookie
visual-regression-scanner https://example.com/sitemap.xml --cookie auth=token123
```

## CLI-Parameter

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `SITEMAP_URL` | - | URL der Sitemap (XML) |
| `--screenshots-dir PATH` | `./screenshots` | Root-Verzeichnis (pro Site ein Unterordner) |
| `--threshold FLOAT` | `0.1` | Diff-Schwelle in Prozent |
| `--viewport WxH` | `1920x1080` | Viewport-Größe |
| `--concurrency N` | `4` | Max parallele Browser-Tabs |
| `--timeout SEC` | `30` | Timeout pro Seite in Sekunden |
| `--rate-limit N` | `60` | Max. Seiten pro Minute (0 = ohne Limit) |
| `--ignore-robots` | `false` | robots.txt ignorieren |
| `--output-json PATH` | - | JSON-Report automatisch speichern |
| `--output-html PATH` | - | HTML-Report automatisch speichern |
| `--no-headless` | `false` | Browser sichtbar starten |
| `--no-full-page` | `false` | Nur sichtbaren Bereich screenshotten |
| `--filter TEXT` | - | Nur URLs die TEXT enthalten |
| `--user-agent UA` | Chrome 131 | Custom User-Agent |
| `--cookie NAME=VALUE` | - | Cookie setzen (mehrfach möglich) |

### Einstellungen

Mit `s` öffnest Du in der TUI die Einstellungen. Sie liegen in
`~/.visual-regression-scanner/settings.json` und umfassen Diff-Schwelle, Viewport,
Ganzseiten-Aufnahme, parallele Tabs, Rate-Limit, Timeout, robots.txt, sichtbaren Browser,
User-Agent, Cookies und Proxy - dazu Sprache und Theme der Oberfläche.

Angaben auf der Kommandozeile haben für den laufenden Aufruf Vorrang, ohne die gespeicherten
Werte zu verändern. Überschrieben wird nur, was Du tatsächlich angibst; alles andere kommt aus
den Einstellungen.

### Bildvorschau und Verlauf

Die Detailansicht zeigt die gewählte Aufnahme direkt im Terminal - umschaltbar zwischen
**Referenz**, **Aktuell** und **Unterschied**. Standardmäßig wird das Bild aus
Unicode-Halbblöcken aufgebaut, was auf jedem Terminal sicher darstellbar ist; für pixelgenaue
Ausgabe über Sixel oder das Kitty-Protokoll schaltest Du in den Einstellungen die *grafische
Vorschau* ein. Der Browser-Vergleich bleibt weiterhin einen Knopfdruck entfernt.

Mit `h` öffnest Du den Verlauf der zuletzt geprüften Sitemaps samt Viewport und Ergebnis - so
wählst Du ein Ziel aus, statt die URL erneut einzutippen.

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| `c` | Scan starten (dynamischer Text, siehe unten) |
| `r` | Reset (alle Bilder löschen + Sitemap neu laden) |
| `R` | Reports speichern (HTML + JSON) |
| `o` | Bilder im Browser öffnen (Lightbox mit Zoom) |
| `l` | Log ein/aus |
| `e` | Nur Diffs anzeigen |
| `/` | Filter fokussieren |
| `s` | Einstellungen |
| `u` | Sitemap-URL eingeben |
| `h` | Verlauf der geprüften Sitemaps |
| `i` | About-Dialog |
| `q` | Beenden |

Die Höhe des Log-Bereichs ziehst Du am Griff darüber. Kopieren, Exportieren und Ausblenden
liegen im Kontextmenü des Log-Bereichs (Rechtsklick).

### Dynamischer Scan-Button

Der Text des Scan-Buttons (`c`) passt sich automatisch an den aktuellen Zustand an:

| Zustand | Button-Text |
|---------|------------|
| Keine Referenz vorhanden | `c Scan (Referenz erstellen)` |
| Referenz vorhanden, keine Aufnahmen | `c Scan (vs. Referenz)` |
| Referenz + Aufnahmen vorhanden | `c Scan (Modus wählen)` |

## Last auf dem Zielsystem - bitte lesen

Für den Screenshot wird jede Seite **vollständig in einem echten Browser gerendert**: Skripte,
Schriften und Bilder werden geladen, der Aufruf läuft an den Zwischenspeichern des Servers vorbei.
Bei Ganzseiten-Aufnahmen wird zusätzlich durch die komplette Seite gescrollt, damit nachgeladene
Inhalte erscheinen. Eine Seite wiegt damit ein Vielfaches eines einfachen HTTP-Abrufs - und ein
Lauf fasst *jede* Seite der Sitemap an.

Der Scanner ist deshalb **von Haus aus gedrosselt**: 60 Seiten pro Minute.

```bash
visual-regression-scanner https://www.example.com/sitemap.xml --rate-limit 20   # schonender
visual-regression-scanner https://www.example.com/sitemap.xml --rate-limit 0    # ohne Limit - Vorsicht
```

`--concurrency` ist **kein** Rate-Limit: Die Einstellung begrenzt, wie viele Browser-Tabs
gleichzeitig laufen, nicht wie viele Seiten pro Minute abgerufen werden.

`robots.txt` wird für die Seiten aus der Sitemap standardmäßig beachtet; gesperrte Seiten werden
übersprungen und im Log ausgewiesen. `--ignore-robots` nur für eigene Systeme verwenden.

## Nutzung auf eigene Verantwortung

Dieses Programm ruft Webseiten automatisiert ab und erzeugt dabei Last auf den Zielsystemen. Je
nach Einstellung kann diese Last die eines normalen Besuchers um ein Vielfaches übersteigen und
die Erreichbarkeit des Zielsystems beeinträchtigen.

Mit der Nutzung erklären Sie:

1. Sie setzen das Programm ausschließlich gegen Systeme ein, für die Ihnen eine ausdrückliche
   Berechtigung des Betreibers vorliegt.
2. Sie tragen die alleinige Verantwortung für den Einsatz, die gewählten Einstellungen und alle
   daraus entstehenden Folgen.
3. Vor einem Lauf gegen ein Produktivsystem prüfen Sie, ob die eingestellten Grenzwerte für
   dieses System angemessen sind.

Die Software wird unentgeltlich und ohne jede Gewährleistung bereitgestellt ("as is"), wie in
Abschnitt 7 der Apache-Lizenz 2.0 beschrieben. Eine Haftung des Autors (Michael Blaess) für
Schäden, die aus der Nutzung entstehen, ist ausgeschlossen, soweit dies gesetzlich zulässig ist.
Unberührt bleibt die Haftung für Vorsatz und grobe Fahrlässigkeit, für Schäden aus der Verletzung
des Lebens, des Körpers oder der Gesundheit sowie nach dem Produkthaftungsgesetz.

Beim ersten Start fragt das Programm diesen Hinweis ab.

## Sprache

Die Oberfläche gibt es vollständig auf **Deutsch** und **Englisch** - Menüs, Meldungen,
Einstellungen, Protokoll und die Kommandozeilen-Hilfe. Umschalten kannst Du in den
Einstellungen (`s`); die Wahl wird gespeichert und gilt ab dem nächsten Start.

Beim allerersten Start entscheidet die Systemumgebung: Deutsch nur bei nachweislich
deutschsprachiger Umgebung, sonst Englisch.

## Workflow

### Erster Scan (Referenz wird automatisch erstellt)

1. `visual-regression-scanner https://example.com/sitemap.xml`
2. Taste `s` - Footer zeigt "Scan (Referenz erstellen)"
3. Screenshots werden erstellt und **automatisch** als Referenz gespeichert, Status "NEU"
4. Danach zeigt der Footer "Scan (vs. Referenz)"

### Zweiter Scan (Vergleich gegen Referenz)

1. Taste `s` - Footer zeigt "Scan (vs. Referenz)"
2. Neue Screenshots werden erstellt und gegen die Referenz verglichen
3. Ergebnis: "OK" (identisch) oder "DIFF" (visueller Unterschied)
4. Danach zeigt der Footer "Scan (Modus waehlen)"

### Folge-Scans (Referenz + Aufnahmen vorhanden)

Wenn bereits Referenz-Bilder UND aktuelle Aufnahmen vorhanden sind,
zeigt der Footer "Scan (Modus waehlen)" und beim Drücken von `s`
erscheint ein Dialog mit zwei Optionen:

**Option A: Erneut scannen**
- Neue Screenshots ersetzen die aktuellen Aufnahmen
- Die Referenz bleibt unverändert
- Vergleich: Neue Screenshots vs. bestehende Referenz

**Option B: Referenz aktualisieren + scannen**
- Die aktuellen Aufnahmen werden zur neuen Referenz
- Alte Referenz wird gelöscht
- Neuer Scan erstellt neue Aufnahmen
- Vergleich: Neue Screenshots vs. neue Referenz (= vorherige Aufnahmen)

### Ergebnisse

- Status "OK" = kein Unterschied, "DIFF" = visuelle Änderung
- Taste `R` (Shift+R) - HTML-Report mit Before/After/Diff-Bildern
- Taste `o` - Bilder im Browser öffnen (Lightbox mit Zoom)

### Ergebnis-Cache

Nach jedem Scan werden die Vergleichs-Ergebnisse in einer `results.json`
im Site-Verzeichnis gespeichert. Beim nächsten Start werden die Ergebnisse
aus dem Cache geladen statt alle Diffs neu zu berechnen. Der Cache wird
automatisch ungültig wenn sich die Bild-Dateien geändert haben.

## Verzeichnisstruktur

Pro Site wird automatisch ein Unterverzeichnis basierend auf dem Hostnamen angelegt:

```
screenshots/
  www.example.com/
    baseline/            # Gespeicherte Referenz-Screenshots
      metadata.json      # URL -> Dateiname Mapping, Zeitstempel
      {url_hash}.png     # Referenz-Bilder (SHA256-Hash der URL)
    current/             # Aktuelle Aufnahmen (letzter Scan)
      {url_hash}.png
    diffs/               # Diff-Bilder (identisch gedimmt, Aenderungen rot)
      {url_hash}.png
    results.json         # Ergebnis-Cache (Diff-Werte + Datei-Timestamps)
  shop.example.com/
    baseline/
    current/
    diffs/
    results.json
```

## Abhängigkeiten

- Python 3.10+
- Textual (TUI-Framework)
- Playwright (Browser-Automation)
- Pillow (Bild-Vergleich)
- httpx (HTTP-Client)
- Rich (Formatierte Ausgabe)

## Release erstellen

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions baut automatisch Executables für Windows, Linux und macOS.
