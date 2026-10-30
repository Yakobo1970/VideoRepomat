"""Zeitliche Glaettung fuer die Frame-fuer-Frame-Kolorierung (DDColor).

DDColor sagt Farbe pro Einzelbild vorher, ohne Wissen ueber Nachbar-Frames -
bei Video fuehrt das zu sichtbarem Farbflackern zwischen aufeinanderfolgenden
Bildern, selbst wenn sich die Szene kaum aendert. Ein einfacher, aber
wirksamer Kompromiss: die Farbkanaele (a/b in Lab) jedes Frames per
exponentiell gleitendem Mittelwert (EMA) mit dem VORHERIGEN, bereits
geglaetteten Frame mischen - der Helligkeitskanal (L) bleibt unangetastet,
damit Schaerfe/Struktur nicht leidet."""
from __future__ import annotations
import cv2
import numpy as np
from PIL import Image


class TemporalColorSmoother:
    def __init__(self, alpha: float = 0.65):
        """alpha: Gewicht des AKTUELLEN Frames (0..1). Niedriger = staerkere
        Glaettung/weniger Flackern, aber mehr "Nachzieh"-Effekt bei schnellen
        Farbwechseln (z.B. Schnitten) - 0.65 ist ein moderater Startwert."""
        self.alpha = alpha
        self._prev_ab: tuple[np.ndarray, np.ndarray] | None = None

    def reset(self):
        """Bei einem Szenenschnitt aufrufen (falls erkannt) oder zu Beginn
        jedes Videos, damit der erste Frame nicht mit einem Rest aus einem
        vorherigen Clip vermischt wird."""
        self._prev_ab = None

    def smooth(self, image: Image.Image) -> Image.Image:
        lab = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2LAB).astype(np.float32)
        l, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]

        if self._prev_ab is not None:
            prev_a, prev_b = self._prev_ab
            a = self.alpha * a + (1 - self.alpha) * prev_a
            b = self.alpha * b + (1 - self.alpha) * prev_b

        self._prev_ab = (a, b)

        lab_out = np.stack([l, a, b], axis=-1)
        lab_out = np.clip(lab_out, 0, 255).astype(np.uint8)
        rgb_out = cv2.cvtColor(lab_out, cv2.COLOR_LAB2RGB)
        return Image.fromarray(rgb_out)
