"""Zentrale App-Identitaet: Name, Version, Links - nur hier aendern, wirkt sich
auf Fenstertitel, About-Dialog und Installer-Beschriftungen aus."""
from pathlib import Path

APP_NAME = "VideoRepomat"
VERSION = "0.1.0"

WEBSITE_URL = "https://www.undabtanzbar.de/software/"
WEBSITE_SECONDARY_URL = "https://yakobo.de"
GITHUB_URL = "https://github.com/Yakobo1970/VideoRepomat"
DONATE_URL = "https://paypal.me/yakobo"

DEFAULT_FILENAME_SUFFIX = " (restored)"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
LOGO_PATH = ASSETS_DIR / "logo.png"
