"""Kapselt alle ffmpeg-Aufrufe: Analyse (Aufloesung/fps/Ton/Interlace),
Frame-Extraktion mit klassischer Filterkette (Deinterlace/Entrauschen/
Deblocking) und Wieder-Zusammensetzen zu einer Videodatei mit Originalton.

Nutzt bewusst NUR das von imageio-ffmpeg mitgelieferte ffmpeg-Binary (kein
System-ffmpeg/ffprobe noetig, keine PATH-Abhaengigkeit) und liest Metadaten
aus ffmpegs eigener stderr-Textausgabe statt ffprobe zu benutzen, da
imageio-ffmpeg kein ffprobe mitliefert."""
from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import imageio_ffmpeg


class JobCancelled(Exception):
    """Interne Abbruch-Markierung, kein echter Fehler - siehe video_pipeline.py."""


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    has_audio: bool
    interlace: str  # "tff" | "bff" | "progressive" | "unknown"


_RESOLUTION_RE = re.compile(r",\s*(\d{2,5})x(\d{2,5})\b")
_FPS_RE = re.compile(r",\s*([\d.]+)\s*fps\b")
_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")


def _run_capture_stderr(args: list[str]) -> str:
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.stderr


def probe(path: Path) -> VideoInfo:
    """Liest Basis-Metadaten aus der Standard-Zusammenfassung, die ffmpeg fuer
    JEDE Eingabedatei nach 'ffmpeg -i <datei>' auf stderr ausgibt (auch ohne
    Ausgabedatei - ffmpeg bricht dann mit Exitcode 1 ab, das ist erwartet und
    kein Fehler, uns interessiert nur der Text)."""
    text = _run_capture_stderr([ffmpeg_exe(), "-i", str(path)])

    video_line = next((l for l in text.splitlines() if "Video:" in l), "")
    audio_present = any("Audio:" in l for l in text.splitlines())

    res_match = _RESOLUTION_RE.search(video_line)
    fps_match = _FPS_RE.search(video_line)
    dur_match = _DURATION_RE.search(text)

    if not res_match:
        raise RuntimeError(f"Konnte Aufloesung nicht aus ffmpeg-Ausgabe lesen:\n{text}")

    width, height = int(res_match.group(1)), int(res_match.group(2))
    fps = float(fps_match.group(1)) if fps_match else 25.0
    if dur_match:
        h, m, s = dur_match.groups()
        duration = int(h) * 3600 + int(m) * 60 + float(s)
    else:
        duration = 0.0

    interlace = _detect_interlace(path)
    return VideoInfo(width=width, height=height, fps=fps, duration=duration, has_audio=audio_present, interlace=interlace)


_IDET_MULTI_RE = re.compile(
    r"Multi frame detection:\s*TFF:\s*(\d+)\s*BFF:\s*(\d+)\s*Progressive:\s*(\d+)\s*Undetermined:\s*(\d+)"
)


def _detect_interlace(path: Path, sample_frames: int = 200) -> str:
    """Laesst ffmpegs 'idet'-Filter ueber die ersten sample_frames laufen und
    wertet die 'Multi frame detection'-Zusammenfassung aus - das ist ffmpegs
    eigene, bewaehrte Interlace-Heuristik, kein selbstgebautes Raten."""
    args = [
        ffmpeg_exe(), "-i", str(path),
        "-frames:v", str(sample_frames),
        "-vf", "idet",
        "-an", "-f", "null", "-",
    ]
    text = _run_capture_stderr(args)
    match = _IDET_MULTI_RE.search(text)
    if not match:
        return "unknown"
    tff, bff, progressive, _undetermined = (int(x) for x in match.groups())
    best = max(("tff", tff), ("bff", bff), ("progressive", progressive), key=lambda kv: kv[1])
    return best[0]


_FRAME_PROGRESS_RE = re.compile(r"frame=\s*(\d+)")


def _run_with_progress(args: list[str], on_frame: Callable[[int], None] | None, should_cancel: Callable[[], bool] | None) -> None:
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    assert proc.stderr is not None
    try:
        for line in proc.stderr:
            if should_cancel is not None and should_cancel():
                proc.terminate()
                proc.wait(timeout=10)
                raise JobCancelled()
            if on_frame is not None:
                match = _FRAME_PROGRESS_RE.search(line)
                if match:
                    on_frame(int(match.group(1)))
        proc.wait()
    finally:
        if proc.poll() is None:
            proc.terminate()
    if proc.returncode not in (0, None) and proc.returncode != 0:
        raise RuntimeError(f"ffmpeg-Aufruf fehlgeschlagen (Code {proc.returncode}): {' '.join(args)}")


def build_filter_chain(deinterlace: bool, denoise: bool, deblock: bool, interlace: str) -> str | None:
    """Reihenfolge ist wichtig: Deinterlacing MUSS vor Entrauschen/Deblocking
    laufen, da beide sonst Kammartefakte aus verschraenkten Feldern als
    'Bilddetail' fehlinterpretieren wuerden."""
    filters: list[str] = []
    if deinterlace and interlace in ("tff", "bff", "unknown"):
        # mode=0 (send_frame, der ffmpeg-Default) gibt EIN Bild pro Vollbild
        # zurueck und erhaelt damit die Original-Framerate/Framezahl. mode=1
        # (send_field) wuerde stattdessen ein Bild pro Halbbild liefern - also
        # die Framezahl verdoppeln, waehrend mux() spaeter mit der originalen
        # fps encodiert. Ergebnis waere ein in Zeitlupe abspielendes Video
        # (beim Testlauf beobachtet: 3s/25fps-Quelle ergab 150 statt 75 Frames).
        filters.append("yadif=0")
    if denoise:
        filters.append("hqdn3d")
    if deblock:
        filters.append("deblock=filter=strong")
    return ",".join(filters) if filters else None


def extract_frames(path: Path, out_dir: Path, filter_chain: str | None,
                    on_frame: Callable[[int], None] | None = None,
                    should_cancel: Callable[[], bool] | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    args = [ffmpeg_exe(), "-y", "-i", str(path)]
    if filter_chain:
        args += ["-vf", filter_chain]
    args += [str(out_dir / "frame_%06d.png")]
    _run_with_progress(args, on_frame, should_cancel)


def extract_audio(path: Path, out_path: Path) -> bool:
    """Codiert die Original-Tonspur nach AAC in eine eigene Datei um (KEIN
    Stream-Copy). Ein Stream-Copy in eine feste Zieldatei (z.B. '.aac') scheitert
    zuverlaessig, sobald der Quellcodec nicht zufaellig schon AAC ist - AVI-
    Quellen aus alten VHS-Rippern liefern oft PCM, VOB-Quellen von DVDs meist
    MP2 (beobachtet: genau das liess einen Testlauf mit VOB-Quelle stillschweigend
    ohne Ton enden, obwohl has_audio korrekt True war). Ein einheitliches
    Ziel-Format zu erzwingen ist fuer diesen Prototyp robuster als den
    Quellcodec zu erkennen und die Zieldatei danach auszurichten. Gibt False
    zurueck, wenn keine Tonspur vorhanden ist oder die Umcodierung fehlschlaegt
    (ffmpeg legt die Zieldatei dabei teils schon leer an, deshalb zusaetzlich
    die Dateigroesse pruefen) - stumme Quellen (z.B. Super-8-Digitalisate ohne
    Ton) sind normal."""
    args = [ffmpeg_exe(), "-y", "-i", str(path), "-vn", "-c:a", "aac", "-b:a", "192k", str(out_path)]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0


def mux(frames_dir: Path, fps: float, out_path: Path, audio_path: Path | None,
        on_frame: Callable[[int], None] | None = None,
        should_cancel: Callable[[], bool] | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        ffmpeg_exe(), "-y",
        "-framerate", str(fps), "-i", str(frames_dir / "frame_%06d.png"),
    ]
    if audio_path is not None and audio_path.exists():
        args += ["-i", str(audio_path), "-c:a", "copy", "-shortest"]
    args += ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(out_path)]
    _run_with_progress(args, on_frame, should_cancel)
