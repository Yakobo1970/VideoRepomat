"""Nur die Graustufen-Erkennung aus PhotoRestore/engine/color_restore.py
uebernommen (is_grayscale) - die uebrigen dortigen Funktionen (Superpixel-
Farbvereinheitlichung etc.) sind fuer den Video-Prototyp nicht relevant und
wuerden nur unnoetige Abhaengigkeiten (scikit-image) mitziehen."""
from __future__ import annotations
import numpy as np
from PIL import Image


def is_grayscale(image: Image.Image, saturation_threshold: float = 8.0, hue_concentration_threshold: float = 0.85) -> bool:
    """Prueft, ob ein Frame praktisch farblos ist - inklusive sepia-/gelbstichiger
    S/W-Aufnahmen. Reine Mittelwert-Saettigung reicht nicht: ein gleichmaessiger
    Alterungs-Farbstich erzeugt eine messbare, aber EINTOENIGE Saettigung ueber
    das ganze Bild, waehrend eine echte Farbaufnahme (auch verblasst) mehrere
    unterschiedliche Farbtoene nebeneinander hat. Deshalb zusaetzlich pruefen,
    wie konzentriert der Farbton (Hue) der ausreichend gesaettigten Pixel ist
    (Kreisvarianz, 1.0 = ein einziger Ton)."""
    hsv = np.array(image.convert("HSV")).astype(np.float32)
    hue, sat = hsv[:, :, 0], hsv[:, :, 1]
    mean_saturation = sat.mean() / 255.0 * 100.0
    if mean_saturation < saturation_threshold:
        return True

    mask = sat > (0.15 * 255)
    if mask.sum() < 0.02 * mask.size:
        return True

    hue_rad = hue[mask] / 255.0 * 2 * np.pi
    resultant_length = np.hypot(np.cos(hue_rad).mean(), np.sin(hue_rad).mean())
    return resultant_length > hue_concentration_threshold
