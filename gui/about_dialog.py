"""About-Dialog im Stil von FlacCheck/Video Motion Detektor: Logo, Beschreibung
(Deutsch/English), Links, Hinweis zur Zuverlaessigkeit und Spenden-Knopf."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout

from app_info import (
    APP_NAME, VERSION, WEBSITE_URL, WEBSITE_SECONDARY_URL, GITHUB_URL, DONATE_URL, LOGO_PATH,
)

ABOUT_HTML_DE = f"""
<h3>Was macht dieses Programm?</h3>
<p>{APP_NAME} versucht, altes, stark degradiertes Videomaterial aufzufrischen – typischerweise
Familienfilme, die einen weiten Weg hinter sich haben (Super 8 &rarr; VHS &rarr; MPEG auf CD/DVD).
Quellen sind AVI- oder VOB-Dateien; das Ergebnis ist ein MP4 mit der originalen Tonspur.</p>

<h3>Kurzanleitung</h3>
<ol>
<li>Quellvideo (AVI/VOB) und Zielordner wählen.</li>
<li>Optionen setzen und „Start“ klicken. Die Vorschau zeigt live den gerade bearbeiteten
Frame – links das Original, rechts das Ergebnis.</li>
<li>Mit „Abbrechen“ lässt sich ein laufender Job jederzeit stoppen.</li>
</ol>

<h3>Optionen</h3>
<ul>
<li><b>Deinterlace</b> – entfernt das Zeilensprung-Muster analoger Aufnahmen.</li>
<li><b>Entrauschen</b> – zeitliches Entrauschen (VHS-Rauschen, Filmkorn).</li>
<li><b>Deblocking</b> – mildert die Klötzchen von MPEG-Kompression (VOB/DVD).</li>
<li><b>Schärfen</b> – Real-ESRGAN pro Frame (verdoppelt dabei die Auflösung).</li>
<li><b>Kolorierung</b> – nur für echtes Schwarzweiß-Material (DDColor mit zeitlicher
Farbglättung); bereits farbige Videos werden automatisch übersprungen.</li>
</ul>

<h3>Wichtiger Hinweis zu den Grenzen</h3>
<p>Bei Material mit mehrfachem Generationsverlust ist Bildinformation <b>verloren</b>, nicht nur
überdeckt. Das Programm kann Rauschen glätten und Kanten schärfen, aber keine Gesichter
rekonstruieren, die im Quellmaterial nur noch als Pixelbrei vorliegen. Das Ergebnis ist ein
<b>Versuch</b> – bitte immer am eigenen Material prüfen. Die Verarbeitung dauert lange
(mehrere Frames pro Sekunde Video) und benötigt eine NVIDIA-Grafikkarte.</p>

<h3>Links</h3>
<p>Website: <a href="{WEBSITE_URL}">www.undabtanzbar.de</a> ·
<a href="{WEBSITE_SECONDARY_URL}">yakobo.de</a><br>
Quellcode und neue Versionen: <a href="{GITHUB_URL}">github.com/Yakobo1970/VideoRepomat</a></p>

<h3>Entwicklung</h3>
<p>Idee, Konzept und Regie: <b>Kay 'Yakobo' Fiedler</b>.<br>
Umgesetzt mit Claude (Anthropic) als KI-Programmierassistent für Architektur, Code und
Fehlersuche – als Geschwister von FotoRepomat.</p>

<h3>Verwendete Komponenten</h3>
<p>Real-ESRGAN (BSD-3-Clause), DDColor (Apache-2.0), FFmpeg (über imageio-ffmpeg), PyTorch, Qt/PySide6.</p>

<h3>Unterstützen</h3>
<p>{APP_NAME} ist kostenlos. Wer die Entwicklung unterstützen möchte, kann über den Knopf unten
eine kleine Spende per PayPal schicken – vielen Dank!</p>
"""

ABOUT_HTML_EN = f"""
<h3>What does this program do?</h3>
<p>{APP_NAME} tries to refresh old, heavily degraded video footage – typically family films that
have been through a lot (Super 8 &rarr; VHS &rarr; MPEG on CD/DVD). Sources are AVI or VOB
files; the result is an MP4 with the original audio track.</p>

<h3>Quick guide</h3>
<ol>
<li>Choose the source video (AVI/VOB) and a target folder.</li>
<li>Set the options and click "Start". The preview shows the frame currently being processed
live – original on the left, result on the right.</li>
<li>"Abbrechen" (Cancel) stops a running job at any time.</li>
</ol>

<h3>Options</h3>
<ul>
<li><b>Deinterlace</b> – removes the interlacing pattern of analog recordings.</li>
<li><b>Entrauschen</b> (denoise) – temporal denoising (VHS noise, film grain).</li>
<li><b>Deblocking</b> – softens MPEG compression blocks (VOB/DVD).</li>
<li><b>Schärfen</b> (sharpen) – Real-ESRGAN per frame (doubles the resolution).</li>
<li><b>Kolorierung</b> (colorize) – only for genuine black-and-white footage (DDColor with
temporal color smoothing); already colored videos are skipped automatically.</li>
</ul>

<h3>Important note on limits</h3>
<p>With footage that has suffered several generations of loss, picture information is
<b>gone</b>, not just covered up. The program can smooth noise and sharpen edges, but it cannot
reconstruct faces that only exist as a blur of pixels in the source. The result is an
<b>experiment</b> – always check it on your own material. Processing is slow (a few frames per
second of video) and requires an NVIDIA graphics card.</p>

<h3>Links</h3>
<p>Website: <a href="{WEBSITE_URL}">www.undabtanzbar.de</a> ·
<a href="{WEBSITE_SECONDARY_URL}">yakobo.de</a><br>
Source code and new versions: <a href="{GITHUB_URL}">github.com/Yakobo1970/VideoRepomat</a></p>

<h3>Development</h3>
<p>Idea, concept and direction: <b>Kay 'Yakobo' Fiedler</b>.<br>
Built with Claude (Anthropic) as an AI coding assistant for architecture, code and debugging –
as a sibling of FotoRepomat.</p>

<h3>Components used</h3>
<p>Real-ESRGAN (BSD-3-Clause), DDColor (Apache-2.0), FFmpeg (via imageio-ffmpeg), PyTorch, Qt/PySide6.</p>

<h3>Support</h3>
<p>{APP_NAME} is free. If you would like to support its development, you can send a small
donation via PayPal using the button below – thank you!</p>
"""


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Über {APP_NAME} {VERSION}")
        self.resize(640, 640)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        logo = QPixmap(str(LOGO_PATH))
        if not logo.isNull():
            icon_label = QLabel(self)
            icon_label.setPixmap(logo.scaledToHeight(84, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(icon_label)
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel(f"<b style='font-size:17pt'>{APP_NAME}</b>", self))
        title_box.addWidget(QLabel(f"Version {VERSION} · Video-Restaurierung (Prototyp)", self))
        header.addSpacing(10)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        tabs = QTabWidget(self)
        for label, html in (("Deutsch", ABOUT_HTML_DE), ("English", ABOUT_HTML_EN)):
            browser = QTextBrowser(self)
            browser.setOpenExternalLinks(True)
            browser.setHtml(html)
            tabs.addTab(browser, label)
        self.tabs = tabs
        layout.addWidget(tabs, stretch=1)

        buttons = QHBoxLayout()
        donate = QPushButton("♥  Spenden via PayPal", self)
        donate.setToolTip(DONATE_URL)
        donate.setStyleSheet("QPushButton { padding: 6px 14px; font-weight: bold; }")
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        web = QPushButton("www.undabtanzbar.de", self)
        web.setToolTip(WEBSITE_URL)
        web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WEBSITE_URL)))
        web2 = QPushButton("yakobo.de", self)
        web2.setToolTip(WEBSITE_SECONDARY_URL)
        web2.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WEBSITE_SECONDARY_URL)))
        close_btn = QPushButton("Schließen", self)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(donate)
        buttons.addWidget(web)
        buttons.addWidget(web2)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
