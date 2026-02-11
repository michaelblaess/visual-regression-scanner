"""Comparator-Service - Pixel-Diff-Vergleich mit Pillow.

Verwendet ausschliesslich schnelle PIL C-Operationen (histogram, point,
composite) statt Python-Pixel-Schleifen. Dadurch auch bei grossen
Full-Page-Screenshots (1920x10000+) in Sekundenbruchteilen fertig.
"""

from __future__ import annotations

from PIL import Image, ImageChops


class Comparator:
    """Vergleicht zwei Screenshots per Pixel-Diff und erzeugt ein Diff-Bild."""

    def __init__(self, threshold: float = 0.1) -> None:
        self.threshold = threshold

    def compare(
        self,
        screenshot_path: str,
        baseline_path: str,
        diff_output_path: str,
    ) -> tuple[float, int, int]:
        """Vergleicht zwei Bilder und erzeugt ein Diff-Bild.

        Args:
            screenshot_path: Pfad zum aktuellen Screenshot.
            baseline_path: Pfad zur Baseline.
            diff_output_path: Pfad fuer das Diff-Bild.

        Returns:
            Tuple aus (diff_percentage, diff_pixel_count, total_pixel_count).
        """
        img_current = Image.open(screenshot_path).convert("RGB")
        img_baseline = Image.open(baseline_path).convert("RGB")

        # Bei unterschiedlicher Groesse: auf gemeinsame Groesse bringen
        current_w, current_h = img_current.size
        baseline_w, baseline_h = img_baseline.size

        if current_w != baseline_w or current_h != baseline_h:
            common_w = min(current_w, baseline_w)
            common_h = min(current_h, baseline_h)
            img_current = img_current.crop((0, 0, common_w, common_h))
            img_baseline = img_baseline.crop((0, 0, common_w, common_h))

        # Pixel-Differenz berechnen (PIL C-Operation)
        diff_img = ImageChops.difference(img_current, img_baseline)

        # Geaenderte Pixel zaehlen via Histogram (schnelle C-Operation)
        # Grayscale: jeder Pixel > 0 bedeutet Aenderung in mindestens einem Kanal
        gray_diff = diff_img.convert("L")
        histogram = gray_diff.histogram()
        total_pixels = img_current.size[0] * img_current.size[1]
        unchanged_pixels = histogram[0]
        changed_pixels = total_pixels - unchanged_pixels

        diff_percentage = (changed_pixels / total_pixels * 100) if total_pixels > 0 else 0.0

        # Diff-Bild erzeugen: identische Pixel gedimmt, geaenderte Pixel rot
        self._create_diff_image(img_current, gray_diff, diff_output_path)

        return diff_percentage, changed_pixels, total_pixels

    def _create_diff_image(
        self,
        img_current: Image.Image,
        gray_diff: Image.Image,
        output_path: str,
    ) -> None:
        """Erzeugt ein visuelles Diff-Bild mit schnellen PIL-Operationen.

        Identische Pixel werden gedimmt dargestellt (50%),
        geaenderte Pixel rot markiert.

        Args:
            img_current: Aktueller Screenshot (RGB).
            gray_diff: Grayscale-Differenzbild.
            output_path: Pfad fuer das Ausgabe-Bild.
        """
        # Maske: 1 wo Pixel sich unterscheiden, 0 wo identisch (C-Operation)
        mask = gray_diff.point(lambda p: 255 if p > 0 else 0).convert("1")

        # Gedimmte Version des aktuellen Screenshots (50% Helligkeit, C-Operation)
        dimmed = img_current.point(lambda p: p // 2)

        # Rote Flaeche fuer geaenderte Pixel
        red = Image.new("RGB", img_current.size, (255, 0, 0))

        # Composite: dimmed wo identisch, rot wo geaendert (C-Operation)
        result = Image.composite(red, dimmed, mask)
        result.save(output_path, "PNG")
