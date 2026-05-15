# Visual Regression Scanner

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <b>English</b> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <a href="README.de.md">Deutsch</a>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/visual-regression-scanner/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/visual-regression-scanner/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/visual-regression-scanner/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/visual-regression-scanner?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/visual-regression-scanner/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/visual-regression-scanner?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/visual-regression-scanner/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

A TUI tool for detecting visual regressions on websites. It automatically creates full-page screenshots of all pages in a sitemap and compares them against stored references via pixel diff.

## Installation

### One-Liner (standalone, no Python required)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/visual-regression-scanner/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/visual-regression-scanner/main/install.ps1 | iex
```

## Features

- **Automatic screenshots** of all URLs from an XML sitemap
- **Pixel-diff comparison** against stored references (baselines)
- **Configurable threshold** for permitted deviations
- **TUI** with live updates, filter, detail view
- **Dynamic scan button** - shows the current state in the footer
- **Result cache** (`results.json`) - avoids recomputation on startup
- **HTML reports** with embedded before/after/diff images (Base64)
- **JSON reports** for CI/CD integration
- **Consent handling** (Usercentrics, OneTrust, CookieBot)
- **Lazy-loading detection** - scrolls through pages and waits for images
- **Parallel processing** with configurable concurrency

## Setup

```bash
# One-time: run setup
setup.bat
```

The setup creates a virtual environment, installs all dependencies, and downloads Chromium.

## Usage

```bash
# Start the TUI
run.bat https://example.com/sitemap.xml

# With increased tolerance
run.bat https://example.com/sitemap.xml --threshold 0.5

# Smaller viewport
run.bat https://example.com/sitemap.xml --viewport 1280x720

# Save HTML report automatically
run.bat https://example.com/sitemap.xml --output-html report.html

# Only specific URLs
run.bat https://example.com/sitemap.xml --filter /produkte

# With auth cookie
run.bat https://example.com/sitemap.xml --cookie auth=token123
```

## CLI Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SITEMAP_URL` | - | URL of the sitemap (XML) |
| `--screenshots-dir PATH` | `./screenshots` | Root directory (one subfolder per site) |
| `--threshold FLOAT` | `0.1` | Diff threshold in percent |
| `--viewport WxH` | `1920x1080` | Viewport size |
| `--concurrency N` | `4` | Max parallel browser tabs |
| `--timeout SEC` | `30` | Timeout per page in seconds |
| `--output-json PATH` | - | Save JSON report automatically |
| `--output-html PATH` | - | Save HTML report automatically |
| `--no-headless` | `false` | Start browser visibly |
| `--no-full-page` | `false` | Screenshot only the visible area |
| `--filter TEXT` | - | Only URLs containing TEXT |
| `--user-agent UA` | Chrome 131 | Custom user agent |
| `--cookie NAME=VALUE` | - | Set cookie (can be used multiple times) |

## Keyboard Shortcuts

| Key | Action |
|-------|--------|
| `s` | Start scan (dynamic text, see below) |
| `r` | Reset (delete all images + reload sitemap) |
| `R` | Save reports (HTML + JSON) |
| `o` | Open images in browser (lightbox with zoom) |
| `l` | Toggle log |
| `e` | Show diffs only |
| `+` / `-` | Adjust log height |
| `/` | Focus filter |
| `c` | Copy log to clipboard |
| `i` | About dialog |
| `q` | Quit |

### Dynamic Scan Button

The text of the scan button (`s`) adapts automatically to the current state:

| State | Button Text |
|---------|------------|
| No reference available | `s Scan (Referenz erstellen)` |
| Reference available, no captures | `s Scan (vs. Referenz)` |
| Reference + captures available | `s Scan (Modus waehlen)` |

## Workflow

### First scan (reference is created automatically)

1. `run.bat https://example.com/sitemap.xml`
2. Press `s` - footer shows "Scan (Referenz erstellen)"
3. Screenshots are created and **automatically** saved as the reference, status "NEU"
4. Afterwards the footer shows "Scan (vs. Referenz)"

### Second scan (comparison against the reference)

1. Press `s` - footer shows "Scan (vs. Referenz)"
2. New screenshots are created and compared against the reference
3. Result: "OK" (identical) or "DIFF" (visual difference)
4. Afterwards the footer shows "Scan (Modus waehlen)"

### Follow-up scans (reference + captures available)

When both reference images AND current captures already exist,
the footer shows "Scan (Modus waehlen)" and pressing `s`
opens a dialog with two options:

**Option A: Scan again**
- New screenshots replace the current captures
- The reference remains unchanged
- Comparison: new screenshots vs. existing reference

**Option B: Update reference + scan**
- The current captures become the new reference
- The old reference is deleted
- A new scan creates new captures
- Comparison: new screenshots vs. new reference (= previous captures)

### Results

- Status "OK" = no difference, "DIFF" = visual change
- Press `R` (Shift+R) - HTML report with before/after/diff images
- Press `o` - open images in browser (lightbox with zoom)

### Result Cache

After each scan, the comparison results are stored in a `results.json`
in the site directory. On the next start, the results are loaded
from the cache instead of recomputing all diffs. The cache is
automatically invalidated when the image files have changed.

## Directory Structure

A subdirectory based on the hostname is created automatically per site:

```
screenshots/
  www.example.com/
    baseline/            # Stored reference screenshots
      metadata.json      # URL -> filename mapping, timestamps
      {url_hash}.png     # Reference images (SHA256 hash of the URL)
    current/             # Current captures (last scan)
      {url_hash}.png
    diffs/               # Diff images (identical areas dimmed, changes in red)
      {url_hash}.png
    results.json         # Result cache (diff values + file timestamps)
  shop.example.com/
    baseline/
    current/
    diffs/
    results.json
```

## Dependencies

- Python 3.10+
- Textual (TUI framework)
- Playwright (browser automation)
- Pillow (image comparison)
- httpx (HTTP client)
- Rich (formatted output)

## Creating a Release

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions automatically builds executables for Windows, Linux, and macOS.
