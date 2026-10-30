"""Real-ESRGAN: generiert zusaetzliche Detailschaerfe auf dem GESAMTEN Frame.
Modell wird beim ersten Gebrauch automatisch von GitHub heruntergeladen und
lokal zwischengespeichert.

(Uebernommen unveraendert aus PhotoRestore/engine/realesrgan_wrapper.py -
arbeitet bereits auf PIL.Image, passt direkt auf einzeln extrahierte Frames.)"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
MODEL_PATH = MODEL_DIR / "RealESRGAN_x4plus.pth"


class RealEsrganDetail:
    def __init__(self, device: str = "cuda", outscale: float = 2.0):
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        if not MODEL_PATH.exists():
            import urllib.request
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        self.upsampler = RealESRGANer(
            scale=4,
            model_path=str(MODEL_PATH),
            model=model,
            tile=512,          # in Kacheln verarbeiten, damit auch grosse Frames ohne VRAM-Ueberlauf laufen
            tile_pad=10,
            pre_pad=0,
            half=(device == "cuda"),
            device=device,
        )
        self.outscale = outscale

    def enhance(self, image: Image.Image) -> Image.Image:
        img_np = np.array(image.convert("RGB"))
        # RealESRGANer erwartet BGR (OpenCV-Konvention)
        img_bgr = img_np[:, :, ::-1]
        output, _ = self.upsampler.enhance(img_bgr, outscale=self.outscale)
        output_rgb = output[:, :, ::-1]
        return Image.fromarray(output_rgb)
