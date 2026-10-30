"""DDColor: koloriert Schwarzweiss-Frames. Laeuft ueber die ModelScope-
Pipeline-API, Modellgewichte werden beim ersten Aufruf automatisch nach
~/.cache/modelscope heruntergeladen.

(Uebernommen unveraendert aus PhotoRestore/engine/ddcolor_wrapper.py.)"""
from __future__ import annotations
import numpy as np
from PIL import Image


class DDColorize:
    def __init__(self, device: str = "cuda"):
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        ms_device = "gpu" if device == "cuda" else "cpu"
        self.pipeline = pipeline(
            Tasks.image_colorization,
            model="damo/cv_ddcolor_image-colorization",
            device=ms_device,
        )

    def colorize(self, image: Image.Image) -> Image.Image:
        from modelscope.outputs import OutputKeys

        img_bgr = np.array(image.convert("RGB"))[:, :, ::-1]
        result = self.pipeline(img_bgr)
        output_bgr = result[OutputKeys.OUTPUT_IMG]
        output_rgb = output_bgr[:, :, ::-1]
        return Image.fromarray(output_rgb.astype("uint8"))
