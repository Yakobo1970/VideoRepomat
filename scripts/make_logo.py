"""Erzeugt assets/icon.png, assets/icon.ico und assets/logo.png im selben
Stil wie FotoRepomat (dicke, runde Strichbuchstaben in Rot/Orange; Logo mit
3D-Abschraegung). Die Buchstaben werden aus Strichen gebaut statt aus einer
Schriftart, damit sie zum Foto-Logo passen.

Aufruf: python scripts/make_logo.py
"""
from __future__ import annotations
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"
RED = (255, 0, 0)
ORANGE = (255, 153, 0)
SS = 4  # Supersampling fuer glatte Kanten


class Canvas:
    """Eine Maske je Farbe; Striche werden mit runden Kappen gezeichnet."""

    def __init__(self, width: int, height: int):
        self.w, self.h = width * SS, height * SS
        self.masks = {"red": Image.new("L", (self.w, self.h), 0), "orange": Image.new("L", (self.w, self.h), 0)}
        self.draws = {k: ImageDraw.Draw(m) for k, m in self.masks.items()}

    def stroke(self, color: str, points, width: float):
        d = self.draws[color]
        pts = [(x * SS, y * SS) for x, y in points]
        w = width * SS
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d.line([(x0, y0), (x1, y1)], fill=255, width=round(w))
        for x, y in pts:
            r = w / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def result(self, size: tuple[int, int]) -> dict[str, np.ndarray]:
        out = {}
        for k, m in self.masks.items():
            out[k] = np.asarray(m.resize(size, Image.LANCZOS), dtype=np.float32) / 255.0
        out["red"] = out["red"] * (1.0 - out["orange"])
        return out


def _arc(cx, cy, rx, ry, a0, a1, n=48):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def letter(cv: Canvas, ch: str, x0: float, y0: float, w: float, h: float, s: float, color: str = "red"):
    """Zeichnet einen Buchstaben in die Zelle (x0,y0,w,h) mit Strichstaerke s."""
    a, b = x0 + s / 2, x0 + w - s / 2
    t, bt = y0 + s / 2, y0 + h - s / 2
    cx, cy = (a + b) / 2, (t + bt) / 2
    st = lambda pts: cv.stroke(color, pts, s)

    if ch == "V":
        st([(a, t), (cx, bt), (b, t)])
    elif ch == "I":
        st([(cx, t), (cx, bt)])
    elif ch == "D":
        rr = (bt - t) / 2
        cxd = max(a, b - rr)
        st([(a, bt), (a, t), (cxd, t)] + _arc(cxd, cy, b - cxd, rr, -90, 90) + [(a, bt)])
    elif ch == "E":
        st([(b, t), (a, t), (a, bt), (b, bt)])
        st([(a, cy), (b - (b - a) * 0.12, cy)])
    elif ch == "O":
        st(_arc(cx, cy, (b - a) / 2, (bt - t) / 2, 0, 360, 72))
    elif ch in "PR":
        tm = t + (bt - t) * (0.56 if ch == "R" else 0.6)
        rr = (tm - t) / 2
        cxd = max(a, b - rr)
        st([(a, bt), (a, t), (cxd, t)] + _arc(cxd, t + rr, b - cxd, rr, -90, 90) + [(a, tm)])
        if ch == "R":
            st([(a + (b - a) * 0.4, tm), (b, bt)])
    elif ch == "M":
        st([(a, bt), (a, t), (cx, t + (bt - t) * 0.62), (b, t), (b, bt)])
    elif ch == "A":
        st([(a, bt), (cx, t), (b, bt)])
        yb = t + (bt - t) * 0.68
        k = (yb - t) / (bt - t)
        st([(cx - (cx - a) * k, yb), (cx + (b - cx) * k, yb)])
    elif ch == "T":
        st([(a, t), (b, t)])
        st([(cx, t), (cx, bt)])
    else:
        raise ValueError(ch)


def row(cv: Canvas, text: str, x: float, y: float, total_w: float, h: float, s: float, gap: float,
        orange: set[int] = frozenset()):
    n = len(text)
    cell = (total_w - gap * (n - 1)) / n
    for i, ch in enumerate(text):
        letter(cv, ch, x + i * (cell + gap), y, cell, h, s, "orange" if i in orange else "red")


def flat_rgba(masks: dict[str, np.ndarray]) -> Image.Image:
    h, w = masks["red"].shape
    total = masks["red"] + masks["orange"]
    alpha = np.clip(total, 0, 1)
    rgb = np.zeros((h, w, 3), np.float32)
    for k, col in (("red", RED), ("orange", ORANGE)):
        rgb += masks[k][..., None] * np.array(col, np.float32)
    rgb = rgb / np.maximum(total[..., None], 1.0)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def bevel_rgba(masks: dict[str, np.ndarray], bevel: float) -> Image.Image:
    """3D-Abschraegung: Hoehenprofil aus der Distanz zum Rand, Beleuchtung von
    links oben, dazu ein weicher Glanzpunkt."""
    h, w = masks["red"].shape
    rgb = np.zeros((h, w, 3), np.float32)
    alpha = np.clip(masks["red"] + masks["orange"], 0, 1)
    light = np.array([-0.55, -0.65, 0.52], np.float32)
    light /= np.linalg.norm(light)
    for k, col in (("red", RED), ("orange", ORANGE)):
        m = masks[k]
        if m.max() <= 0:
            continue
        dist = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        height = np.sin(np.clip(dist / bevel, 0, 1) * math.pi / 2)
        height = cv2.GaussianBlur(height, (0, 0), 0.8)
        gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) * bevel * 0.9
        gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) * bevel * 0.9
        nz = np.ones_like(gx)
        norm = np.sqrt(gx * gx + gy * gy + nz * nz)
        lam = np.clip((-gx / norm) * light[0] + (-gy / norm) * light[1] + (nz / norm) * light[2], 0, 1)
        shade = 0.30 + 0.95 * lam
        spec = np.power(lam, 14) * 0.55
        base = np.array(col, np.float32)
        layer = np.clip(base[None, None, :] * shade[..., None] + 255 * spec[..., None], 0, 255)
        rgb += layer * m[..., None]
    rgb = rgb / np.maximum((masks["red"] + masks["orange"])[..., None], 1.0)
    out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def build_icon(size: int = 512) -> Image.Image:
    cv = Canvas(size, size)
    m = size * 0.04
    s = size * 0.06
    row_h = size * 0.40
    top, bottom = size * 0.07, size * 0.07 + row_h + size * 0.12
    span = size - 2 * m
    gap = size * 0.028
    row(cv, "VIDEO", m, top, span, row_h, s, gap, orange={4})
    row(cv, "REPO", m, bottom, span, row_h, s, gap * 1.4, orange={3})
    return flat_rgba(cv.result((size, size)))


def build_logo(width: int = 900) -> Image.Image:
    height = round(width * 0.62)
    cv = Canvas(width, height)
    m = width * 0.02
    s_big = width * 0.05
    big_h = height * 0.56
    gap = width * 0.025
    span = width - 2 * m
    row(cv, "VIDEO", m, height * 0.03, span, big_h, s_big, gap, orange={4})
    s_small = width * 0.021
    row(cv, "REPOMAT", m, height * 0.66, span, height * 0.28, s_small, width * 0.012, orange={3})
    return bevel_rgba(cv.result((width, height)), bevel=width * 0.019)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = build_icon(512)
    icon.save(ASSETS / "icon.png")
    icon.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    build_logo(900).save(ASSETS / "logo.png")
    print("geschrieben:", ASSETS)


if __name__ == "__main__":
    main()
