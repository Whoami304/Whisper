"""Make "press Run and it starts" true.

Before any Qt import, check that the required packages load. If they don't,
install what's needed into the interpreter that is running right now (the
project's .venv when started from PyCharm or run.bat) and restart once.

The common Windows failure this fixes:
    ImportError: DLL load failed while importing QtCore:
    The specified procedure could not be found.
PyQt5 5.15.11 is built against Qt 5.15.14, but the newest Qt wheel published
for Windows is PyQt5-Qt5 5.15.2. PyQt5 5.15.10 matches it.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")
_FLAG = "WHISPER_DEPS_REPAIRED"
_MODULES = ("PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
            "numpy", "PIL.Image", "cryptography", "mutagen")
_WIN_PYQT_PIN = ["PyQt5==5.15.10", "PyQt5-Qt5==5.15.2"]


def _problem():
    """None if everything imports, otherwise the error text."""
    for name in _MODULES:
        try:
            __import__(name)
        except ImportError as exc:      # includes ModuleNotFoundError and DLL errors
            return "%s: %s" % (name, exc)
    return None


def _pip(args):
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + args
    print("Whisper: installing dependencies ->", " ".join(args), flush=True)
    return subprocess.call(cmd) == 0


def _alert(text):
    print(text, file=sys.stderr, flush=True)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "Whisper", 0x10)
        except Exception:
            pass


def ensure():
    problem = _problem()
    if problem is None:
        return
    if os.environ.get(_FLAG):            # already tried once; don't loop
        _alert("Whisper can't start because a required package doesn't load:\n\n%s\n\n"
               "Run setup.bat in the Whisper folder, then try again." % problem)
        sys.exit(1)

    print("Whisper: %s" % problem, file=sys.stderr, flush=True)
    ok = _pip(["-r", REQUIREMENTS])
    if ok and sys.platform == "win32":
        ok = _pip(_WIN_PYQT_PIN)         # downgrades a broken PyQt5 5.15.11
    if not ok:
        _alert("Whisper couldn't install its dependencies automatically.\n\n"
               "Check the internet connection and run setup.bat in the Whisper folder.")
        sys.exit(1)

    # Restart in a fresh process: the failed import has left this one unusable.
    env = dict(os.environ, **{_FLAG: "1"})
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))
