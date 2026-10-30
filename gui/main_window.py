"""Schlankes Prototyp-Hauptfenster: eine Datei auswaehlen, Optionen setzen,
starten - keine Ordner-Batch/Mehrfachauswahl wie bei FotoRepomat, das ist fuer
den ersten Qualitaets-Versuch bewusst nicht noetig.

Live-Vorschau-Mechanismus (zwei ImagePreviewWidget, aktualisiert ueber das
frame_done-Signal aus gui/video_worker.py) ist der direkte Analog zu
PhotoRestore/gui/main_window.py::_on_batch_image_done - dort aktualisiert das
Signal nach jedem fertigen BILD das Ziel-Panel, hier nach jedem fertigen
FRAME beide Panels (Original- und Verarbeitet-Ansicht)."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QCheckBox, QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar, QMessageBox,
)

from app_info import APP_NAME, VERSION, DEFAULT_FILENAME_SUFFIX
from engine.video_pipeline import VideoRestorePipeline, VideoRestoreOptions
from gui.zoomable_image_view import ImagePreviewWidget
from gui.progress_window import ProgressWindow
from gui.about_dialog import AboutDialog
from gui.video_worker import start_video_job

SOURCE_FILTER = "Videos (*.avi *.vob);;Alle Dateien (*)"


def _next_free_output_path(src_path: Path, target_folder: Path) -> Path:
    candidate = target_folder / f"{src_path.stem}{DEFAULT_FILENAME_SUFFIX}.mp4"
    n = 2
    while candidate.exists():
        candidate = target_folder / f"{src_path.stem}{DEFAULT_FILENAME_SUFFIX} {n}.mp4"
        n += 1
    return candidate


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1200, 750)

        self.pipeline = VideoRestorePipeline(device="cuda")
        self._thread = None
        self._worker = None
        self._src_path: Path | None = None
        self._target_folder: Path | None = None

        self.progress_window = ProgressWindow(self)

        self._build_ui()

        help_menu = self.menuBar().addMenu("Hilfe")
        about_action = help_menu.addAction(f"Über {APP_NAME} ...")
        about_action.triggered.connect(lambda: AboutDialog(self).exec())

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # --- Dateiauswahl ---
        file_row = QHBoxLayout()
        self.source_edit = QLineEdit(self)
        self.source_edit.setReadOnly(True)
        self.source_edit.setPlaceholderText("Keine Datei ausgewaehlt (AVI/VOB)")
        source_button = QPushButton("Datei waehlen ...", self)
        source_button.clicked.connect(self._choose_source)
        file_row.addWidget(QLabel("Quelle:", self))
        file_row.addWidget(self.source_edit, stretch=1)
        file_row.addWidget(source_button)
        root_layout.addLayout(file_row)

        target_row = QHBoxLayout()
        self.target_edit = QLineEdit(self)
        self.target_edit.setReadOnly(True)
        self.target_edit.setPlaceholderText("Kein Zielordner ausgewaehlt")
        target_button = QPushButton("Zielordner waehlen ...", self)
        target_button.clicked.connect(self._choose_target)
        target_row.addWidget(QLabel("Ziel:", self))
        target_row.addWidget(self.target_edit, stretch=1)
        target_row.addWidget(target_button)
        root_layout.addLayout(target_row)

        # --- Optionen ---
        options_box = QGroupBox("Optionen", self)
        options_layout = QHBoxLayout(options_box)
        self.check_deinterlace = QCheckBox("Deinterlace", self)
        self.check_deinterlace.setChecked(True)
        self.check_denoise = QCheckBox("Entrauschen", self)
        self.check_denoise.setChecked(True)
        self.check_deblock = QCheckBox("Deblocking (MPEG/VOB)", self)
        self.check_deblock.setChecked(True)
        self.check_sharpen = QCheckBox("Schaerfen (Real-ESRGAN)", self)
        self.check_sharpen.setChecked(True)
        self.check_colorize = QCheckBox("Kolorierung (nur falls S/W erkannt)", self)
        self.check_colorize.setChecked(False)
        for cb in (self.check_deinterlace, self.check_denoise, self.check_deblock,
                   self.check_sharpen, self.check_colorize):
            options_layout.addWidget(cb)
        root_layout.addWidget(options_box)

        # --- Start/Abbrechen + Fortschritt ---
        run_row = QHBoxLayout()
        self.run_button = QPushButton("Start", self)
        self.run_button.clicked.connect(self._on_run_clicked)
        self.status_label = QLabel("Bereit.", self)
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.status_label, stretch=1)
        root_layout.addLayout(run_row)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        root_layout.addWidget(self.progress_bar)

        # --- Live-Vorschau: Original | Verarbeitet ---
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.original_preview = ImagePreviewWidget("Original-Frame", self)
        self.processed_preview = ImagePreviewWidget("Verarbeiteter Frame", self)
        splitter.addWidget(self.original_preview)
        splitter.addWidget(self.processed_preview)
        splitter.setSizes([600, 600])
        root_layout.addWidget(splitter, stretch=1)

    # --- Dateiauswahl ---

    def _choose_source(self):
        path_str, _ = QFileDialog.getOpenFileName(self, "Quellvideo waehlen", "", SOURCE_FILTER)
        if not path_str:
            return
        self._src_path = Path(path_str)
        self.source_edit.setText(str(self._src_path))
        if self._target_folder is None:
            self._target_folder = self._src_path.parent
            self.target_edit.setText(str(self._target_folder))

    def _choose_target(self):
        folder_str = QFileDialog.getExistingDirectory(self, "Zielordner waehlen")
        if not folder_str:
            return
        self._target_folder = Path(folder_str)
        self.target_edit.setText(str(self._target_folder))

    def _current_options(self) -> VideoRestoreOptions:
        return VideoRestoreOptions(
            deinterlace=self.check_deinterlace.isChecked(),
            denoise=self.check_denoise.isChecked(),
            deblock=self.check_deblock.isChecked(),
            sharpen=self.check_sharpen.isChecked(),
            colorize=self.check_colorize.isChecked(),
        )

    # --- Start/Abbrechen ---

    def _on_run_clicked(self):
        if self._worker is not None:
            self._worker.request_cancel()
            self.run_button.setEnabled(False)
            self.status_label.setText("Breche ab ...")
            return

        if self._src_path is None or self._target_folder is None:
            QMessageBox.warning(self, "Fehlende Auswahl", "Bitte zuerst Quelldatei und Zielordner waehlen.")
            return

        dst_path = _next_free_output_path(self._src_path, self._target_folder)

        self.original_preview.clear()
        self.processed_preview.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starte ...")
        self.run_button.setText("Abbrechen")
        self.progress_window.reset("Starte ...")
        self.progress_window.show()
        self.progress_window.raise_()

        self._thread, self._worker = start_video_job(
            self.pipeline, self._src_path, dst_path, self._current_options(),
            on_progress=self._on_progress,
            on_frame_progress=self._on_frame_progress,
            on_frame_done=self._on_frame_done,
            on_finished=self._on_finished,
            on_failed=self._on_failed,
        )

    def _on_progress(self, step: str):
        self.status_label.setText(step)
        self.progress_window.on_step(step)

    def _on_frame_progress(self, index: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index)

    def _on_frame_done(self, index: int, total: int, original_path: str, processed_path: str):
        self.original_preview.show_image(original_path, title=f"Original - Frame {index}/{total}")
        self.processed_preview.show_image(processed_path, title=f"Verarbeitet - Frame {index}/{total}")

    def _release_thread(self):
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

    def _on_finished(self, dst_path: str):
        self.status_label.setText(f"Fertig: {Path(dst_path).name}")
        self.progress_window.on_finished(success=True)
        self.run_button.setText("Start")
        self.run_button.setEnabled(True)
        self._release_thread()

    def _on_failed(self, message: str):
        self.status_label.setText(message)
        self.progress_window.on_finished(success=False)
        self.run_button.setText("Start")
        self.run_button.setEnabled(True)
        self._release_thread()

    def closeEvent(self, event):
        if self._worker is not None:
            answer = QMessageBox.question(
                self, "Job laeuft noch",
                "Ein Restaurierungsjob laeuft noch. Wirklich beenden? Der laufende Vorgang wird abgebrochen.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.request_cancel()
            if self._thread is not None:
                self._thread.quit()
                if not self._thread.wait(30000):
                    QMessageBox.warning(
                        self, "Job reagiert nicht",
                        "Der Vorgang beendet sich nicht rechtzeitig (evtl. mitten in einem ffmpeg-Schritt). "
                        "Bitte kurz warten und erneut versuchen.",
                    )
                    event.ignore()
                    return
                self._thread = None
                self._worker = None
        super().closeEvent(event)
