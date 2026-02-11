# Visual Regression Scanner

TUI-Tool zur Erkennung visueller Regressionen auf Websites. Erstellt automatisch Full-Page-Screenshots aller Seiten einer Sitemap und vergleicht sie gegen gespeicherte Referenzen per Pixel-Diff.

## Features

- **Automatische Screenshots** aller URLs aus einer XML-Sitemap
- **Pixel-Diff-Vergleich** gegen gespeicherte Referenzen (Baselines)
- **Konfigurierbare Schwelle** (Threshold) fuer erlaubte Abweichungen
- **TUI** mit Live-Updates, Filter, Detail-Ansicht
- **Dynamischer Scan-Button** - zeigt den aktuellen Zustand im Footer
- **Ergebnis-Cache** (`results.json`) - vermeidet Neuberechnung beim Start
- **HTML-Reports** mit eingebetteten Before/After/Diff-Bildern (Base64)
- **JSON-Reports** fuer CI/CD-Integration
- **Consent-Handling** (Usercentrics, OneTrust, CookieBot)
- **Lazy-Loading-Erkennung** - scrollt Seiten durch und wartet auf Bilder
- **Parallele Verarbeitung** mit konfigurierbarer Concurrency

## Setup

```bash
# Einmalig: Setup ausfuehren
setup.bat
```

Das Setup erstellt eine virtuelle Umgebung, installiert alle Abhaengigkeiten und laedt Chromium herunter.

## Verwendung

```bash
# TUI starten
run.bat https://example.com/sitemap.xml

# Mit erhoehter Toleranz
run.bat https://example.com/sitemap.xml --threshold 0.5

# Kleinerer Viewport
run.bat https://example.com/sitemap.xml --viewport 1280x720

# HTML-Report automatisch speichern
run.bat https://example.com/sitemap.xml --output-html report.html

# Nur bestimmte URLs
run.bat https://example.com/sitemap.xml --filter /produkte

# Mit Auth-Cookie
run.bat https://example.com/sitemap.xml --cookie auth=token123
```

## CLI-Parameter

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `SITEMAP_URL` | - | URL der Sitemap (XML) |
| `--screenshots-dir PATH` | `./screenshots` | Root-Verzeichnis (pro Site ein Unterordner) |
| `--threshold FLOAT` | `0.1` | Diff-Schwelle in Prozent |
| `--viewport WxH` | `1920x1080` | Viewport-Groesse |
| `--concurrency N` | `4` | Max parallele Browser-Tabs |
| `--timeout SEC` | `30` | Timeout pro Seite in Sekunden |
| `--output-json PATH` | - | JSON-Report automatisch speichern |
| `--output-html PATH` | - | HTML-Report automatisch speichern |
| `--no-headless` | `false` | Browser sichtbar starten |
| `--no-full-page` | `false` | Nur sichtbaren Bereich screenshotten |
| `--filter TEXT` | - | Nur URLs die TEXT enthalten |
| `--user-agent UA` | Chrome 131 | Custom User-Agent |
| `--cookie NAME=VALUE` | - | Cookie setzen (mehrfach moeglich) |

## Tastenkuerzel

| Taste | Aktion |
|-------|--------|
| `s` | Scan starten (dynamischer Text, siehe unten) |
| `r` | Reset (alle Bilder loeschen + Sitemap neu laden) |
| `R` | Reports speichern (HTML + JSON) |
| `o` | Bilder im Browser oeffnen (Lightbox mit Zoom) |
| `l` | Log ein/aus |
| `e` | Nur Diffs anzeigen |
| `+` / `-` | Log-Hoehe anpassen |
| `/` | Filter fokussieren |
| `c` | Log in Zwischenablage kopieren |
| `i` | About-Dialog |
| `q` | Beenden |

### Dynamischer Scan-Button

Der Text des Scan-Buttons (`s`) passt sich automatisch an den aktuellen Zustand an:

| Zustand | Button-Text |
|---------|------------|
| Keine Referenz vorhanden | `s Scan (Referenz erstellen)` |
| Referenz vorhanden, keine Aufnahmen | `s Scan (vs. Referenz)` |
| Referenz + Aufnahmen vorhanden | `s Scan (Modus waehlen)` |

## Workflow

### Erster Scan (Referenz wird automatisch erstellt)

1. `run.bat https://example.com/sitemap.xml`
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
zeigt der Footer "Scan (Modus waehlen)" und beim Druecken von `s`
erscheint ein Dialog mit zwei Optionen:

**Option A: Erneut scannen**
- Neue Screenshots ersetzen die aktuellen Aufnahmen
- Die Referenz bleibt unveraendert
- Vergleich: Neue Screenshots vs. bestehende Referenz

**Option B: Referenz aktualisieren + scannen**
- Die aktuellen Aufnahmen werden zur neuen Referenz
- Alte Referenz wird geloescht
- Neuer Scan erstellt neue Aufnahmen
- Vergleich: Neue Screenshots vs. neue Referenz (= vorherige Aufnahmen)

### Ergebnisse

- Status "OK" = kein Unterschied, "DIFF" = visuelle Aenderung
- Taste `R` (Shift+R) - HTML-Report mit Before/After/Diff-Bildern
- Taste `o` - Bilder im Browser oeffnen (Lightbox mit Zoom)

### Ergebnis-Cache

Nach jedem Scan werden die Vergleichs-Ergebnisse in einer `results.json`
im Site-Verzeichnis gespeichert. Beim naechsten Start werden die Ergebnisse
aus dem Cache geladen statt alle Diffs neu zu berechnen. Der Cache wird
automatisch ungueltig wenn sich die Bild-Dateien geaendert haben.

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

## Abhaengigkeiten

- Python 3.10+
- Textual (TUI-Framework)
- Playwright (Browser-Automation)
- Pillow (Bild-Vergleich)
- httpx (HTTP-Client)
- Rich (Formatierte Ausgabe)
