"""Fuehrt einen Video-Restaurierungsjob in einem Hintergrund-Thread aus.

Thread-Pattern 1:1 uebernommen aus PhotoRestore/gui/batch_worker.py: QObject
per moveToThread in einen QThread verlagert, Fortschritt/Ergebnis ausschliesslich
per Qt-Signal in den GUI-Thread gemeldet (kein Polling), Abbruch ueber ein
Flag, das der progress_cb-Callback der Pipeline zwischen den Schritten prueft."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from engine.ffmpeg_tools import JobCancelled
from engine.video_pipeline import VideoRestorePipeline, VideoRestoreOptions


class VideoWorker(QObject):
    progress = Signal(str)                      # aktueller Teilschritt
    frame_progress = Signal(int, int)            # Index, Gesamtanzahl - fuer den Fortschrittsbalken
    frame_done = Signal(int, int, str, str)      # Index, Gesamt, Original-Frame-Pfad, Verarbeiteter-Frame-Pfad
    finished = Signal(str)                       # Ausgabepfad
    failed = Signal(str)                         # Fehlermeldung (auch bei Abbruch durch Nutzer)

    def __init__(self, pipeline: VideoRestorePipeline, src_path: Path, dst_path: Path, options: VideoRestoreOptions):
        super().__init__()
        self.pipeline = pipeline
        self.src_path = src_path
        self.dst_path = dst_path
        self.options = options
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def _on_progress(self, step: str):
        self.progress.emit(step)

    def _on_frame(self, index: int, total: int, original_path: str, processed_path: str):
        self.frame_progress.emit(index, total)
        self.frame_done.emit(index, total, original_path, processed_path)

    def run(self):
        try:
            self.pipeline.run(
                self.src_path, self.dst_path, self.options,
                progress_cb=self._on_progress,
                frame_cb=self._on_frame,
                should_cancel=lambda: self._cancel_requested,
            )
            self.finished.emit(str(self.dst_path))
        except JobCancelled:
            self.failed.emit("Abgebrochen durch Nutzer.")
        except Exception as exc:  # noqa: BLE001 - dem Nutzer als Fehlermeldung anzeigen
            self.failed.emit(f"{type(exc).__name__}: {exc}")


def start_video_job(pipeline: VideoRestorePipeline, src_path: Path, dst_path: Path, options: VideoRestoreOptions,
                     on_progress, on_frame_progress, on_frame_done, on_finished, on_failed):
    """Startet den Job in einem QThread. Der Aufrufer MUSS (thread, worker)
    am Leben halten (z.B. als self._thread/self._worker), sonst raeumt Python
    sie vorzeitig weg - siehe Warnung in PhotoRestore/gui/batch_worker.py."""
    thread = QThread()
    worker = VideoWorker(pipeline, src_path, dst_path, options)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.frame_progress.connect(on_frame_progress)
    worker.frame_done.connect(on_frame_done)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
