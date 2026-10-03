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


# --- interaction model and theming --------------------------------------

def _shown_main_window():
    from gui.StartWindow.mainWindow import MainWindow
    window = MainWindow()
    window.show()
    QtWidgets.QApplication.setActiveWindow(window)
    QtWidgets.QApplication.processEvents()
    return window


def test_mouse_click_never_leaves_a_focus_outline(app):
    from PyQt5 import QtCore, QtTest
    window = _shown_main_window()
    window.ui.openHideMessageWindow()
    page = window.ui.hide_page
    for button in (page.key.toggle, page.mode.buttons[1], page.embed_btn, page.back_btn):
        assert button.focusPolicy() == QtCore.Qt.TabFocus
    QtTest.QTest.mouseClick(page.key.toggle, QtCore.Qt.LeftButton)
    assert QtWidgets.QApplication.focusWidget() is not page.key.toggle
    assert page.carrier.zone.focusPolicy() == QtCore.Qt.TabFocus
    window.close()


def test_opening_a_page_keeps_the_window_active(app):
    # Regression: a separator shown before it had a parent became a window
    # of its own for a moment and stole activation/focus on every page switch.
    window = _shown_main_window()
    window.ui.openHideMessageWindow()
    QtWidgets.QApplication.processEvents()
    assert QtWidgets.QApplication.activeWindow() is window
    window.close()


def test_text_box_tab_moves_focus(app):
    from gui.HideMessage.hideMessage import HidePage
    page = HidePage()
    assert page.payload_edit.tabChangesFocus()


def test_theme_switch_keeps_what_was_typed(app):
    window = _shown_main_window()
    ui = window.ui
    ui.openHideMessageWindow()
    page = ui.hide_page
    page.payload_edit.setPlainText("keep me")
    page.key.setText("pw-123-abc")
    before = theme.MODE
    theme.switch_theme(animate=False)
    try:
        assert theme.MODE != before
        assert ui.hide_page is page                       # not rebuilt
        assert page.payload_edit.toPlainText() == "keep me"
        assert page.key.text() == "pw-123-abc"
        assert theme.BG == (theme.DARK if theme.MODE == "dark" else theme.LIGHT)["BG"]
    finally:
        theme.switch_theme(before, animate=False)
        window.close()
