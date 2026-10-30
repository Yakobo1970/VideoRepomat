# VideoRepomat

![VideoRepomat](assets/logo.png)

Video-Restaurierung für altes, stark degradiertes Filmmaterial (Super 8 → VHS →
MPEG auf CD/DVD) – als Geschwister-Projekt zu
[FotoRepomat](https://github.com/Yakobo1970/FotoRepomat). Quellen sind AVI- oder
VOB-Dateien, das Ergebnis ist ein MP4 mit der originalen Tonspur. Die GUI zeigt
während der Verarbeitung live Original- und Ergebnis-Frame nebeneinander.

**Status: Prototyp (v0.1.0).** Ein erster Qualitäts-Versuch, kein fertiges
Produkt. Ob und wie stark die Pipeline bei stark degradiertem Material sichtbar
hilft, muss am eigenen Material geprüft werden.

Website: <https://www.undabtanzbar.de/software/> · <https://yakobo.de>

## Warum anders als FotoRepomat

FotoRepomat repariert lokale Schäden (Kratzer, Risse) an Fotos, bei denen die
Bildinformation drumherum noch vollständig vorhanden ist. Videomaterial mit
mehrfachem Generationsverlust (Super 8 → VHS → MPEG) hat dagegen Bildinformation
*strukturell verloren*, nicht nur lokal überdeckt. Deshalb liegt der Fokus hier
auf klassischen Verfahren (Deinterlacing, zeitliches Entrauschen,
MPEG-Deblocking) plus KI-Schärfung – Kratzer-Inpainting (LaMa) wurde bewusst
nicht übernommen.

## Pipeline

1. **ffmpeg-Filterkette** beim Extrahieren der Frames: Deinterlace (`yadif`) →
   Entrauschen (`hqdn3d`) → Deblocking (`deblock`)
2. **Real-ESRGAN** pro Frame (Schärfen, verdoppelt die Auflösung) – optional
3. **DDColor** pro Frame (Kolorierung) mit zeitlicher Farbglättung gegen
   Flackern – optional, nur bei erkanntem Schwarzweiß-Material
4. **ffmpeg-Remux** zu MP4 (H.264) mit Original-Framerate und Original-Ton
   (nach AAC umkodiert)

Jeder Schritt lässt sich in der GUI einzeln zu- und abschalten; ein laufender
Job kann jederzeit abgebrochen werden.

## Installation (Windows)

Den Installer **`VideoRepomat-0.1.0-Setup.exe`** unter
[Releases](https://github.com/Yakobo1970/VideoRepomat/releases) herunterladen
und starten. Er installiert pro Benutzer (keine Admin-Rechte nötig) und richtet
beim ersten Setup eine eigene, isolierte Miniconda-Umgebung im App-Ordner ein.
PyTorch/CUDA und alle Abhängigkeiten werden dabei nachgeladen (mehrere GB,
je nach Verbindung 5–15 Minuten). Das System-Python bleibt unberührt.

Weil der Installer nicht signiert ist, zeigt Windows SmartScreen beim ersten
Start eventuell eine Warnung („Weitere Informationen“ → „Trotzdem ausführen“).

**Voraussetzung:** NVIDIA-Grafikkarte mit CUDA. Es gibt keinen CPU-Fallback.
Für RTX-50xx-Karten (Blackwell) wird automatisch ein passender
PyTorch-Build (`cu128`) installiert.

Die Modell-Gewichte (Real-ESRGAN, DDColor) werden erst beim ersten Gebrauch der
jeweiligen Option automatisch nachgeladen.

## Aus dem Quellcode starten

```powershell
conda create -n videorestore -c conda-forge --override-channels python=3.11
conda activate videorestore
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
python main.py
```

Für schnelle Tests ohne GUI:

```powershell
python scripts/cli_test.py quelle.avi ziel.mp4
```

## Bekannte Grenzen

- Bei mehrfachem Generationsverlust ist Bildinformation verloren: Rauschen und
  Kanten lassen sich verbessern, Gesichter, die im Quellmaterial nur noch als
  Pixelbrei vorliegen, nicht rekonstruieren.
- Die Verarbeitung ist rechenintensiv (Real-ESRGAN läuft pro Frame) – ein
  Film von einigen Minuten braucht entsprechend lange.
- Die Interlace-Erkennung ist eine Heuristik (ffmpegs `idet`-Filter); im
  Zweifel „Deinterlace“ in der GUI manuell testen.
- Nur der Ablauf mit synthetischen Testdateien und die klassische Filterkette
  samt Real-ESRGAN-Schärfung sind bisher ausführlich getestet; die Kolorierung
  ist noch nicht an echtem Material erprobt.

## Entstehung

Idee, Konzept und Regie: Kay „Yakobo“ Fiedler. Umgesetzt in enger
Zusammenarbeit mit **Claude (Anthropic)** als KI-Programmierassistent –
Architektur, Pipeline, GUI und Installer.

## Unterstützen

VideoRepomat ist kostenlos. Wer die Entwicklung unterstützen möchte:
<https://paypal.me/yakobo>

## Lizenz

MIT für den eigenen Code (siehe [LICENSE](LICENSE)). Verwendete Komponenten
(Real-ESRGAN, DDColor, PyTorch, Qt/PySide6, FFmpeg über imageio-ffmpeg) stehen
unter ihren eigenen Lizenzen.
