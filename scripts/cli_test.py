"""Headloser Test der Pipeline an einer einzelnen Datei, ohne GUI - fuer
schnelle Iteration an echtem AVI/VOB-Material.

Aufruf:
    python scripts/cli_test.py <quelle.avi> <ziel.mp4> [--no-sharpen] [--colorize] [--no-denoise] [--no-deblock] [--no-deinterlace]
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.video_pipeline import VideoRestorePipeline, VideoRestoreOptions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--no-deinterlace", action="store_true")
    parser.add_argument("--no-denoise", action="store_true")
    parser.add_argument("--no-deblock", action="store_true")
    parser.add_argument("--no-sharpen", action="store_true")
    parser.add_argument("--colorize", action="store_true")
    args = parser.parse_args()

    options = VideoRestoreOptions(
        deinterlace=not args.no_deinterlace,
        denoise=not args.no_denoise,
        deblock=not args.no_deblock,
        sharpen=not args.no_sharpen,
        colorize=args.colorize,
    )

    def on_progress(step: str):
        print(f"[{time.strftime('%H:%M:%S')}] {step}")

    def on_frame(index: int, total: int, original_path: str, processed_path: str):
        if index == 1 or index % 25 == 0 or index == total:
            print(f"  Frame {index}/{total}")

    pipeline = VideoRestorePipeline(device="cuda")
    t0 = time.time()
    pipeline.run(args.source, args.target, options, progress_cb=on_progress, frame_cb=on_frame)
    print(f"Fertig in {time.time() - t0:.1f}s -> {args.target}")


if __name__ == "__main__":
    main()
