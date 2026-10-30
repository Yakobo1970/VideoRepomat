"""Orchestriert die Video-Restaurierung: ffmpeg-Extraktion (Deinterlace/
Entrauschen/Deblocking) -> Frame-fuer-Frame KI-Nachbearbeitung (Schaerfen,
optional Kolorierung) -> ffmpeg-Remux mit Originalton.

Architektur bewusst analog zu PhotoRestore/engine/pipeline.py: eine
Options-Dataclass mit einfachen Bool-Schaltern, lazy geladene/gecachte
Modell-Wrapper, ein progress_cb der pro Schritt aufgerufen wird und ueber den
Abbruch signalisiert werden kann (siehe _JobCancelled)."""
from __future__ import annotations

from engine import _compat  # noqa: F401  muss vor basicsr/realesrgan importiert werden

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from engine import ffmpeg_tools
from engine.ffmpeg_tools import JobCancelled
from engine.color_restore import is_grayscale
from engine.color_temporal import TemporalColorSmoother


@dataclass
class VideoRestoreOptions:
    deinterlace: bool = True
    denoise: bool = True
    deblock: bool = True
    sharpen: bool = True
    colorize: bool = False


# JobCancelled wird aus ffmpeg_tools uebernommen (nicht neu definiert), damit
# ein Abbruch waehrend der ffmpeg-Phase (extract_frames/mux) UND ein Abbruch
# waehrend der Python-Frame-Schleife (siehe step() unten) vom Aufrufer
# (gui/video_worker.py) mit demselben except-Zweig abgefangen werden koennen.


def _looks_like_gpu_context_error(exc: Exception) -> bool:
    """Uebernommen aus PhotoRestore/gui/batch_worker.py: ein einzelner harter
    CUDA-Fehler beschaedigt oft den gesamten CUDA-Kontext des Prozesses - bei
    Video mit potenziell tausenden GPU-Aufrufen pro Datei noch wahrscheinlicher
    als bei einem Einzelfoto. Weitermachen waere aussichtslos, deshalb sofortiger
    Abbruch des gesamten Laufs statt Frame-fuer-Frame denselben Fehler zu sammeln."""
    text = f"{type(exc).__name__} {exc}".lower()
    markers = ("cuda error", "cudnn error", "cufft", "accelerator error", "cuda out of memory", "cuda_error", "cublas")
    return any(m in text for m in markers)


class VideoRestorePipeline:
    def __init__(self, device: str = "cuda"):
        self.device = device
        self._realesrgan = None
        self._ddcolor = None

    def _get_realesrgan(self):
        if self._realesrgan is None:
            from engine.realesrgan_wrapper import RealEsrganDetail
            self._realesrgan = RealEsrganDetail(self.device)
        return self._realesrgan

    def _get_ddcolor(self):
        if self._ddcolor is None:
            from engine.ddcolor_wrapper import DDColorize
            self._ddcolor = DDColorize(self.device)
        return self._ddcolor

    def run(self, src_path: Path, dst_path: Path, options: VideoRestoreOptions,
            progress_cb: Callable[[str], None] | None = None,
            frame_cb: Callable[[int, int, str, str], None] | None = None,
            should_cancel: Callable[[], bool] | None = None) -> None:
        progress_cb = progress_cb or (lambda step: None)
        cancel_check = should_cancel or (lambda: False)

        def step(text: str):
            if cancel_check():
                raise JobCancelled()
            progress_cb(text)

        temp_root = Path(tempfile.mkdtemp(prefix="videorepomat_"))
        original_dir = temp_root / "original"
        processed_dir = temp_root / "processed"
        audio_path = temp_root / "audio.m4a"
        processed_dir.mkdir(parents=True, exist_ok=True)

        try:
            step("Analysiere Quelldatei ...")
            info = ffmpeg_tools.probe(src_path)

            step("Extrahiere Frames (Deinterlace/Entrauschen/Deblocking) ...")
            filter_chain = ffmpeg_tools.build_filter_chain(
                options.deinterlace, options.denoise, options.deblock, info.interlace,
            )
            total_estimate = max(1, round(info.duration * info.fps)) if info.duration else 0
            ffmpeg_tools.extract_frames(
                src_path, original_dir, filter_chain,
                on_frame=lambda n: progress_cb(f"Extrahiere Frame {n}/{total_estimate or '?'} ..."),
                should_cancel=cancel_check,
            )

            has_audio = False
            if info.has_audio:
                step("Extrahiere Tonspur ...")
                has_audio = ffmpeg_tools.extract_audio(src_path, audio_path)

            frame_files = sorted(original_dir.glob("frame_*.png"))
            total = len(frame_files)
            if total == 0:
                raise RuntimeError("Keine Frames extrahiert - Quelldatei vermutlich nicht lesbar.")

            colorize_this_video = False
            if options.colorize:
                with Image.open(frame_files[0]) as first_frame:
                    colorize_this_video = is_grayscale(first_frame)
                if not colorize_this_video:
                    progress_cb("Quelle ist bereits farbig - Kolorierung wird uebersprungen.")

            smoother = TemporalColorSmoother() if colorize_this_video else None

            for index, frame_path in enumerate(frame_files, start=1):
                step(f"Verarbeite Frame {index}/{total} ...")

                image = Image.open(frame_path).convert("RGB")

                if options.sharpen:
                    image = self._get_realesrgan().enhance(image)

                if colorize_this_video:
                    image = self._get_ddcolor().colorize(image)
                    image = smoother.smooth(image)

                out_path = processed_dir / frame_path.name
                image.save(out_path)

                if frame_cb is not None:
                    frame_cb(index, total, str(frame_path), str(out_path))

                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            step("Setze Video wieder zusammen ...")
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            ffmpeg_tools.mux(
                processed_dir, info.fps, dst_path,
                audio_path if has_audio else None,
                should_cancel=cancel_check,
            )

        except Exception as exc:
            if not isinstance(exc, JobCancelled) and _looks_like_gpu_context_error(exc):
                raise RuntimeError(
                    "GPU-Fehler erkannt - der CUDA-Kontext ist vermutlich beschaedigt und laesst sich in "
                    "diesem Programmlauf nicht mehr reparieren. Bitte VideoRepomat neu starten und erneut "
                    f"versuchen. Urspruenglicher Fehler: {type(exc).__name__}: {exc}"
                ) from exc
            raise
        else:
            shutil.rmtree(temp_root, ignore_errors=True)
