"""Einstiegspunkt fuer VideoRepomat (GUI)."""
import os
import sys
from pathlib import Path

# Unter pythonw.exe (kein Konsolenfenster, z.B. Desktop-Verknuepfung/Installer)
# sind sys.stdout/sys.stderr None statt eines Stream-Objekts. Real-ESRGAN gibt
# seinen Kachel-Fortschritt per print() aus - das wuerde dann mit
# "AttributeError: 'NoneType' object has no attribute 'write'" abstuerzen,
# aber erst mitten im ersten Frame mit aktivem Schaerfen.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import threading

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QSplashScreen

# gui.main_window bewusst NICHT hier oben importieren - das zieht ueber
# engine.video_pipeline -> engine._compat den ersten torch/torchvision-Import
# nach sich (mehrere Sekunden), noch bevor ueberhaupt eine QApplication
# existiert. Ohne Splash sieht der Nutzer in dieser Zeit gar nichts.
from app_info import APP_NAME, VERSION, ICON_PATH, LOGO_PATH


def main():
    if sys.platform == "win32":
        # Ohne eigene AppUserModelID gruppiert Windows das Taskleisten-Icon
        # unter dem generischen python.exe-Icon statt unter unserem eigenen.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"undabtanzbar.{APP_NAME}.{VERSION}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(ICON_PATH)))

    logo = QPixmap(str(LOGO_PATH))
    logo = logo.scaledToWidth(380, Qt.TransformationMode.SmoothTransformation)
    text_area_height = 32
    canvas = QPixmap(logo.width(), logo.height() + text_area_height)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap(0, 0, logo)
    painter.end()

    splash = QSplashScreen(canvas, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
    splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    splash.showMessage(
        f"{APP_NAME} wird gestartet ...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.white,
    )
    splash.show()
    app.processEvents()

    # Der schwere Import (torch) blockiert mehrere Sekunden. Im Hintergrund-
    # Thread importieren und im Haupt-Thread weiter Events verarbeiten, sonst
    # haelt Windows die App fuer eingefroren und ersetzt den transparenten
    # Splash-Hintergrund durch eine schwarze Flaeche.
    imported: dict = {}

    def import_main_window():
        from gui.main_window import MainWindow
        imported["MainWindow"] = MainWindow

    import_thread = threading.Thread(target=import_main_window, daemon=True)
    import_thread.start()
    while import_thread.is_alive():
        app.processEvents()
        import_thread.join(0.05)

    window = imported["MainWindow"]()
    window.show()
    splash.finish(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
