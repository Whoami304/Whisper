"""Build a standalone Whisper executable with PyInstaller.

    pip install -r requirements.txt pyinstaller
    python build_exe.py

Result: dist/Whisper.exe on Windows (dist/Whisper elsewhere) -- one file that
runs without Python or any packages installed. Check it with:

    dist\\Whisper.exe --selftest
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build")


def make_icon(path):
    """Draw the app icon (white padlock on an accent tile) into a .ico file."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, ROOT)
    import gui  # noqa: F401
    from PyQt5 import QtCore, QtWidgets
    from gui import theme

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    theme.set_mode("light")
    pngs = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = theme.app_icon().pixmap(size, size)
        p = os.path.join(BUILD, "icon_%d.png" % size)
        pm.save(p, "PNG")
        pngs.append(p)
    del app
    from PIL import Image
    big = Image.open(pngs[-1]).convert("RGBA")
    big.save(path, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])


def main():
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(BUILD, "whisper.ico")
    make_icon(icon)
    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", "Whisper",
        "--icon", icon,
        "--paths", os.path.join(ROOT, "Whisper"),
        "--hidden-import", "engine",
        "--hidden-import", "legacy",
        "--hidden-import", "gui.HideMessage.hideMessage",
        "--hidden-import", "gui.RevealContent.revealContent",
        "--add-data", "%s%s." % (os.path.join(ROOT, "SECURITY.md"), sep),
        # Qt modules Whisper never uses -- keeps the exe small.
        "--exclude-module", "tkinter",
        "--exclude-module", "PyQt5.QtWebEngineWidgets",
        "--exclude-module", "PyQt5.QtWebEngineCore",
        "--exclude-module", "PyQt5.QtQml",
        "--exclude-module", "PyQt5.QtQuick",
        "--exclude-module", "PyQt5.QtMultimedia",
        "--exclude-module", "PyQt5.QtNetwork",
        "--exclude-module", "PyQt5.QtSql",
        "--exclude-module", "PyQt5.QtTest",
        "--exclude-module", "pytest",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(BUILD, "pyinstaller"),
        "--specpath", BUILD,
        os.path.join(ROOT, "app.py"),
    ]
    print(" ".join(args), flush=True)
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
