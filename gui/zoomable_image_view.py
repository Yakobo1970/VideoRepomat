"""Zoom- und pan-faehige Bildvorschau (Mausrad = zoomen, Ziehen = verschieben)
fuer den Frame-Vergleich Original/Verarbeitet waehrend eines laufenden Jobs.

Vereinfachte Fassung von PhotoRestore/gui/zoomable_image_view.py: die
Video-Pipeline erzeugt ausschliesslich PNG-Frames, daher entfaellt hier die
dortige RAW/HEIC/JPEG-XL-Sonderbehandlung sowie der Logo-Platzhalter."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel, QVBoxLayout, QWidget


class ZoomableImageView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 0

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.set_background_color("#141414")

    def set_background_color(self, hex_color: str):
        self.setStyleSheet(f"background-color: {hex_color}; border: none;")

    def clear(self):
        self._scene.clear()
        self._pixmap_item = None

    def load_image(self, path: str | Path) -> bool:
        try:
            pixmap = QPixmap(str(path))
        except Exception:
            pixmap = QPixmap()
        if pixmap.isNull():
            self.clear()
            return False
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._zoom = 0
        self.fit_to_view()
        return True

    def image_size(self) -> tuple[int, int] | None:
        if self._pixmap_item is None:
            return None
        pixmap = self._pixmap_item.pixmap()
        return (pixmap.width(), pixmap.height())

    def fit_to_view(self):
        if self._pixmap_item is None:
            return
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 0

    def wheelEvent(self, event):
        if self._pixmap_item is None:
            return
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        new_zoom = self._zoom + (1 if event.angleDelta().y() > 0 else -1)
        if -10 <= new_zoom <= 25:
            self.scale(factor, factor)
            self._zoom = new_zoom

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item is not None and self._zoom == 0:
            self.fit_to_view()

    def mouseDoubleClickEvent(self, event):
        self.fit_to_view()
        super().mouseDoubleClickEvent(event)


class ImagePreviewWidget(QWidget):
    """Bildvorschau + Titelzeile (zeigt Frame-Info)."""

    def __init__(self, placeholder_text: str = "Kein Frame geladen", parent=None):
        super().__init__(parent)
        self.view = ZoomableImageView(self)
        self.title_label = QLabel(placeholder_text, self)
        self.title_label.setStyleSheet("color: palette(window-text); padding: 4px;")
        self.title_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.view, stretch=1)

        self._placeholder_text = placeholder_text

    def show_image(self, path: str | Path, title: str | None = None):
        ok = self.view.load_image(path)
        if ok:
            self.title_label.setText(title if title is not None else str(path))
        else:
            self.title_label.setText(f"Konnte Bild nicht laden: {path}")

    def clear(self):
        self.view.clear()
        self.title_label.setText(self._placeholder_text)
