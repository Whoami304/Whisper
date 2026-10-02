"""Smoke tests: every page builds and the workers run end to end (offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt5.QtWidgets")

from gui import theme                                   # noqa: E402
from gui.StartWindow.mainWindow import Ui_MainWindow    # noqa: E402
from gui.HideMessage.hideMessage import EmbedWorker, MODE_TEXT     # noqa: E402
from gui.RevealContent.revealContent import ExtractWorker, RevealPage  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    theme.apply(a)
    return a


def test_windows_build(app):
    window = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(window)
    ui.openHideMessageWindow()
    ui.openRevealContentWindow()
    ui.goHome()
    window.close()


def test_workers_roundtrip(app, png, tmp_path):
    out = str(tmp_path / "o.png")
    hide = EmbedWorker(MODE_TEXT, png, "gui secret", "gui-password-123!", out)
    errors = []
    hide.failed.connect(errors.append)
    hide.run()
    assert not errors and os.path.exists(out)

    results = []
    reveal = ExtractWorker(out, "gui-password-123!")
    reveal.recovered.connect(results.append)
    reveal.failed.connect(errors.append)
    reveal.run()
    assert not errors and results[0].text == "gui secret"

    page = RevealPage()
    page._on_recovered(results[0])
    assert page.result_text.toPlainText() == "gui secret"


def test_reveal_wrong_password_reports_error(app, png):
    errors = []
    w = ExtractWorker(png, "whatever")
    w.failed.connect(errors.append)
    w.run()
    assert errors and "password" in errors[0].lower()
