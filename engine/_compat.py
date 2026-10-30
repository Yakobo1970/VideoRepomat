"""Kompatibilitaets-Shims fuer Bibliotheken, die seit laengerem nicht mehr
aktualisiert wurden (v.a. basicsr), aber mit aktuellem torchvision (>=0.17)
kollidieren. Muss VOR dem ersten Import von basicsr/realesrgan ausgefuehrt
werden - deshalb ganz oben in video_pipeline.py importiert.

(Uebernommen unveraendert aus PhotoRestore/engine/_compat.py.)"""
import sys
import types

try:
    import torchvision.transforms.functional_tensor  # noqa: F401
except ModuleNotFoundError:
    # torchvision >=0.17 hat functional_tensor entfernt und die Funktionen
    # nach torchvision.transforms.functional verschoben. basicsr (Real-ESRGAN-
    # Abhaengigkeit) importiert noch den alten Pfad - hier als Shim
    # nachbilden, damit der Import nicht crasht.
    import torchvision.transforms.functional as F

    shim = types.ModuleType("torchvision.transforms.functional_tensor")
    shim.rgb_to_grayscale = F.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = shim
