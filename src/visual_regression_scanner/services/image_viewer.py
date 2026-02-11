"""Image-Viewer - Oeffnet eine HTML-Vergleichsansicht im Browser."""

from __future__ import annotations

import base64
import os
import tempfile
import webbrowser

from ..models.scan_result import ComparisonStatus, ScreenshotResult


def open_comparison_view(result: ScreenshotResult) -> str | None:
    """Erzeugt eine HTML-Vergleichsansicht und oeffnet sie im Browser.

    Zeigt Baseline, aktuellen Screenshot und Diff-Bild nebeneinander
    als Thumbnails. Klick oeffnet eine Lightbox mit Prev/Next-Navigation.

    Args:
        result: Das ScreenshotResult mit Bildpfaden.

    Returns:
        Pfad zur erzeugten HTML-Datei oder None bei Fehler.
    """
    images = _collect_images(result)
    if not images:
        return None

    html = _build_viewer_html(result, images)

    # Temp-Datei erstellen und im Browser oeffnen
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".html",
        prefix="vrs_compare_",
        delete=False,
        encoding="utf-8",
    )
    tmp.write(html)
    tmp.close()

    webbrowser.open(f"file:///{tmp.name}")
    return tmp.name


def _collect_images(result: ScreenshotResult) -> list[dict]:
    """Sammelt verfuegbare Bilder als Base64 mit Label.

    Args:
        result: Das ScreenshotResult.

    Returns:
        Liste von Dicts mit 'label' und 'data' (Base64).
    """
    images = []

    if result.baseline_path and os.path.exists(result.baseline_path):
        images.append({
            "label": "Baseline",
            "data": _image_to_base64(result.baseline_path),
        })

    if result.screenshot_path and os.path.exists(result.screenshot_path):
        images.append({
            "label": "Aktuell",
            "data": _image_to_base64(result.screenshot_path),
        })

    if result.diff_path and os.path.exists(result.diff_path):
        images.append({
            "label": f"Diff ({result.diff_percentage:.2f}%)",
            "data": _image_to_base64(result.diff_path),
        })

    return images


def _image_to_base64(path: str) -> str:
    """Liest ein Bild und konvertiert es zu Base64.

    Args:
        path: Pfad zum Bild.

    Returns:
        Base64-kodierter String.
    """
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _build_viewer_html(result: ScreenshotResult, images: list[dict]) -> str:
    """Erzeugt das HTML fuer die Vergleichsansicht mit Lightbox.

    Args:
        result: Das ScreenshotResult.
        images: Liste der Bilder mit Label und Base64-Daten.

    Returns:
        Vollstaendiger HTML-String.
    """
    # Status-Info
    status_text = result.status_icon
    diff_info = ""
    if result.diff_percentage > 0:
        diff_info = f" | Diff: {result.diff_percentage:.4f}% | Pixel: {result.diff_pixel_count:,} / {result.total_pixel_count:,}"

    # Thumbnail-Cards erzeugen (volle Breite, Seite an Seite)
    thumb_cards = []
    for idx, img in enumerate(images):
        thumb_cards.append(
            f'<div class="thumb-card" onclick="openLightbox({idx})">'
            f'  <div class="thumb-img-wrap">'
            f'    <img src="data:image/png;base64,{img["data"]}" alt="{img["label"]}">'
            f'  </div>'
            f'  <div class="thumb-label">{img["label"]}</div>'
            f'</div>'
        )

    # Lightbox-Slides erzeugen (mit img-container fuer Zoom/Pan)
    slides = []
    for idx, img in enumerate(images):
        slides.append(
            f'<div class="slide" id="slide-{idx}">'
            f'  <div class="img-container" id="container-{idx}">'
            f'    <img src="data:image/png;base64,{img["data"]}" alt="{img["label"]}">'
            f'  </div>'
            f'  <div class="slide-label">{img["label"]}</div>'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VRS - {_html_escape(result.url)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 16px; }}

.header {{ margin-bottom: 16px; }}
.header h1 {{ color: #58a6ff; font-size: 1.2rem; margin-bottom: 6px; }}
.header .meta {{ color: #8b949e; font-size: 0.85rem; }}
.header a {{ color: #58a6ff; text-decoration: none; }}
.header a:hover {{ text-decoration: underline; }}

/* Thumbnails - grosse Vorschau, Seite an Seite */
.thumbs {{
    display: flex; gap: 12px; margin-bottom: 12px;
}}
.thumb-card {{
    flex: 1 1 0; min-width: 0;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 8px; cursor: pointer; transition: border-color 0.2s, transform 0.15s;
    display: flex; flex-direction: column;
}}
.thumb-card:hover {{ border-color: #58a6ff; transform: translateY(-2px); }}
.thumb-card .thumb-img-wrap {{
    flex: 1; overflow: hidden; border-radius: 4px;
    max-height: calc(100vh - 140px);
}}
.thumb-card .thumb-img-wrap img {{
    width: 100%; display: block; border-radius: 4px;
}}
.thumb-label {{
    text-align: center; margin-top: 8px; font-size: 0.85rem;
    font-weight: 600; color: #c9d1d9; flex-shrink: 0;
}}

/* Lightbox */
.lightbox {{
    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.95); z-index: 1000; justify-content: center; align-items: center;
}}
.lightbox.active {{ display: flex; }}
.slide {{ display: none; text-align: center; max-width: 95%; max-height: 95%; overflow: hidden; }}
.slide.active {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}
.slide .img-container {{
    overflow: auto; max-width: 90vw; max-height: 85vh; position: relative;
    cursor: zoom-in;
}}
.slide .img-container.zoomed {{ cursor: grab; }}
.slide .img-container.zoomed.dragging {{ cursor: grabbing; }}
.slide .img-container img {{
    display: block; max-width: 90vw; max-height: 85vh; object-fit: contain;
    border: 1px solid #30363d; border-radius: 4px;
    transition: transform 0.15s ease;
    transform-origin: center center;
}}
.slide .img-container.zoomed img {{
    max-width: none; max-height: none; cursor: grab;
}}
.slide-label {{
    color: #c9d1d9; font-size: 1.1rem; font-weight: 600;
    margin-top: 12px;
}}
.zoom-info {{
    position: fixed; bottom: 50px; left: 50%; transform: translateX(-50%);
    color: #8b949e; font-size: 0.8rem; z-index: 1001;
}}

/* Navigation */
.nav-btn {{
    position: fixed; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,0.1); border: none; color: #c9d1d9;
    font-size: 2.5rem; width: 60px; height: 80px; cursor: pointer;
    border-radius: 8px; z-index: 1001; transition: background 0.2s;
    display: flex; align-items: center; justify-content: center;
}}
.nav-btn:hover {{ background: rgba(255,255,255,0.2); }}
.nav-prev {{ left: 15px; }}
.nav-next {{ right: 15px; }}
.close-btn {{
    position: fixed; top: 15px; right: 20px;
    background: none; border: none; color: #8b949e;
    font-size: 2rem; cursor: pointer; z-index: 1001;
}}
.close-btn:hover {{ color: #c9d1d9; }}
.counter {{
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    color: #8b949e; font-size: 0.9rem; z-index: 1001;
}}
.hint {{
    text-align: center; color: #484f58; font-size: 0.8rem;
}}
</style>
</head>
<body>

<div class="header">
    <h1>Visual Regression Scanner</h1>
    <div class="meta">
        <a href="{_html_escape(result.url)}" target="_blank">{_html_escape(result.url)}</a>
        <br>Status: {status_text} | HTTP {result.http_status_code} | {result.load_time_ms / 1000:.1f}s{diff_info}
    </div>
</div>

<div class="thumbs">
    {''.join(thumb_cards)}
</div>

<p class="hint">Klick = Lightbox | Scroll = Zoom | Klick auf Bild = 200% | Pfeiltasten | +/- Zoom | 0 = Reset | ESC</p>

<div class="lightbox" id="lightbox">
    <button class="close-btn" onclick="closeLightbox()">&times;</button>
    <button class="nav-btn nav-prev" onclick="prevSlide()">&#8249;</button>
    <button class="nav-btn nav-next" onclick="nextSlide()">&#8250;</button>
    {''.join(slides)}
    <div class="counter" id="counter"></div>
    <div class="zoom-info" id="zoom-info"></div>
</div>

<script>
var currentSlide = 0;
var totalSlides = {len(images)};
var zoomLevel = 1;
var isDragging = false;
var hasDragged = false;
var dragStartX = 0, dragStartY = 0;
var scrollStartX = 0, scrollStartY = 0;

/* Feste Zoom-Stufen fuer Klick-Cycling */
var ZOOM_STEPS = [1, 2, 4];
var currentZoomStep = 0;

function openLightbox(idx) {{
    currentSlide = idx;
    document.getElementById('lightbox').classList.add('active');
    resetZoom();
    showSlide();
    document.body.style.overflow = 'hidden';
}}

function closeLightbox() {{
    document.getElementById('lightbox').classList.remove('active');
    document.body.style.overflow = '';
    resetZoom();
}}

function showSlide() {{
    for (var i = 0; i < totalSlides; i++) {{
        var el = document.getElementById('slide-' + i);
        if (el) el.classList.toggle('active', i === currentSlide);
    }}
    document.getElementById('counter').textContent = (currentSlide + 1) + ' / ' + totalSlides;
    resetZoom();
}}

function nextSlide() {{
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide();
}}

function prevSlide() {{
    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    showSlide();
}}

function resetZoom() {{
    zoomLevel = 1;
    currentZoomStep = 0;
    var container = document.getElementById('container-' + currentSlide);
    if (!container) return;
    var img = container.querySelector('img');
    if (img) img.style.transform = 'scale(1)';
    container.classList.remove('zoomed', 'dragging');
    container.scrollTop = 0;
    container.scrollLeft = 0;
    updateZoomInfo();
}}

function applyZoom(container, newZoom, centerX, centerY) {{
    var img = container.querySelector('img');
    if (!img) return;

    var oldZoom = zoomLevel;
    zoomLevel = Math.max(0.5, Math.min(newZoom, 10));

    if (zoomLevel <= 1.05) {{
        zoomLevel = 1;
        currentZoomStep = 0;
        img.style.transform = 'scale(1)';
        container.classList.remove('zoomed');
        container.scrollTop = 0;
        container.scrollLeft = 0;
    }} else {{
        img.style.transform = 'scale(' + zoomLevel + ')';
        container.classList.add('zoomed');

        if (oldZoom > 0 && centerX !== undefined) {{
            var ratio = zoomLevel / oldZoom;
            var newScrollLeft = (container.scrollLeft + centerX) * ratio - centerX;
            var newScrollTop = (container.scrollTop + centerY) * ratio - centerY;
            container.scrollLeft = newScrollLeft;
            container.scrollTop = newScrollTop;
        }}
    }}
    updateZoomInfo();
}}

function updateZoomInfo() {{
    var info = document.getElementById('zoom-info');
    if (zoomLevel > 1.05) {{
        info.textContent = Math.round(zoomLevel * 100) + '% | Scroll = Zoom | Klick = naechste Stufe | Doppelklick = Anpassen';
    }} else {{
        info.textContent = 'Scroll = Zoom | Klick = 200% | Doppelklick = Anpassen';
    }}
}}

// Scroll-Zoom (sanftere Schritte: 10% statt 15%)
document.addEventListener('wheel', function(e) {{
    var lb = document.getElementById('lightbox');
    if (!lb.classList.contains('active')) return;

    var container = document.getElementById('container-' + currentSlide);
    if (!container) return;

    e.preventDefault();
    var rect = container.getBoundingClientRect();
    var centerX = e.clientX - rect.left;
    var centerY = e.clientY - rect.top;

    var delta = e.deltaY > 0 ? -0.1 : 0.1;
    applyZoom(container, zoomLevel * (1 + delta), centerX, centerY);
}}, {{ passive: false }});

// Klick = feste Zoom-Stufen durchschalten (1x -> 2x -> 4x -> 1x)
document.addEventListener('click', function(e) {{
    var lb = document.getElementById('lightbox');
    if (!lb.classList.contains('active')) return;

    var container = e.target.closest('.img-container');
    if (!container) return;
    if (hasDragged) {{ hasDragged = false; return; }}

    var rect = container.getBoundingClientRect();
    var clickX = e.clientX - rect.left;
    var clickY = e.clientY - rect.top;

    // Naechste Zoom-Stufe
    currentZoomStep = (currentZoomStep + 1) % ZOOM_STEPS.length;
    var targetZoom = ZOOM_STEPS[currentZoomStep];

    if (targetZoom <= 1) {{
        resetZoom();
    }} else {{
        applyZoom(container, targetZoom, clickX, clickY);
    }}
}});

// Doppelklick = Reset
document.addEventListener('dblclick', function(e) {{
    var lb = document.getElementById('lightbox');
    if (!lb.classList.contains('active')) return;
    var container = e.target.closest('.img-container');
    if (!container) return;
    e.preventDefault();
    resetZoom();
}});

// Drag-to-Pan
document.addEventListener('mousedown', function(e) {{
    var container = e.target.closest('.img-container.zoomed');
    if (!container) return;
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    scrollStartX = container.scrollLeft;
    scrollStartY = container.scrollTop;
    container.classList.add('dragging');
    e.preventDefault();
}});

document.addEventListener('mousemove', function(e) {{
    if (!isDragging) return;
    var dx = e.clientX - dragStartX;
    var dy = e.clientY - dragStartY;
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasDragged = true;
    var container = document.getElementById('container-' + currentSlide);
    if (!container) return;
    container.scrollLeft = scrollStartX - dx;
    container.scrollTop = scrollStartY - dy;
}});

document.addEventListener('mouseup', function() {{
    if (!isDragging) return;
    isDragging = false;
    var container = document.getElementById('container-' + currentSlide);
    if (container) container.classList.remove('dragging');
}});

document.addEventListener('keydown', function(e) {{
    var lb = document.getElementById('lightbox');
    if (!lb.classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') nextSlide();
    if (e.key === 'ArrowLeft') prevSlide();
    if (e.key === '+' || e.key === '=') {{
        var c = document.getElementById('container-' + currentSlide);
        if (c) {{ var r = c.getBoundingClientRect(); applyZoom(c, zoomLevel * 1.25, r.width/2, r.height/2); }}
    }}
    if (e.key === '-') {{
        var c = document.getElementById('container-' + currentSlide);
        if (c) {{ var r = c.getBoundingClientRect(); applyZoom(c, zoomLevel / 1.25, r.width/2, r.height/2); }}
    }}
    if (e.key === '0') resetZoom();
}});
</script>

</body>
</html>"""


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
