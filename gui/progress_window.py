"""Separates, frei skalierbares Fenster, das die einzelnen Pipeline-Schritte
live mitprotokolliert - bei Video (potenziell tausende Frames) noch wichtiger
als bei Fotos, um erkennen zu koennen, dass der Job aktiv arbeitet statt haengt.

(Uebernommen unveraendert aus PhotoRestore/gui/progress_window.py.)"""
from __future__ import annotations
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QProgressBar


class ProgressWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Verarbeitung")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(440, 420)

        self.current_label = QLabel("Bereit.", self)
        self.current_label.setWordWrap(True)
        self.current_label.setStyleSheet("font-weight: bold;")

        self.busy_bar = QProgressBar(self)
        self.busy_bar.setRange(0, 0)  # unbestimmt = pulsierend, solange der aktuelle Schritt laeuft
        self.busy_bar.setVisible(False)

        self.log_list = QListWidget(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.current_label)
        layout.addWidget(self.busy_bar)
        layout.addWidget(self.log_list, stretch=1)

        self._step_start: float | None = None
        self._current_item: QListWidgetItem | None = None

    def reset(self, title: str = ""):
        self.log_list.clear()
        self.current_label.setText(title or "Bereit.")
        self.busy_bar.setVisible(False)
        self._step_start = None
        self._current_item = None

    def _mark_current_done(self):
        if self._current_item is not None and self._step_start is not None:
            elapsed = time.time() - self._step_start
            self._current_item.setText(f"✓ {self._current_item.text()}  ({elapsed:.1f}s)")
        self._current_item = None
        self._step_start = None

    def on_step(self, text: str):
        self._mark_current_done()
        item = QListWidgetItem(f"⏳ {text}")
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()
        self._current_item = item
        self._step_start = time.time()
        self.current_label.setText(text)
        self.busy_bar.setVisible(True)

    def on_finished(self, success: bool = True):
        self._mark_current_done()
        self.current_label.setText("Fertig." if success else "Fehlgeschlagen.")
        self.busy_bar.setVisible(False)
