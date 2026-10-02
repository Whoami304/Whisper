"""Whisper's main window: a home screen plus the Hide and Read pages.

Everything lives in one window with a QStackedWidget, so moving between
screens doesn't close and reopen windows (which made the window jump
around and lose its size).
"""

import os
import sys

if __package__ in (None, ""):          # started as a script, e.g. from PyCharm
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt5 import QtCore, QtGui, QtWidgets

import gui
from gui import theme


class ChoiceCard(QtWidgets.QPushButton):
    """A large clickable card on the home screen."""

    def __init__(self, icon_name, title, description, cta, parent=None):
        super(ChoiceCard, self).__init__(parent)
        self.setObjectName("choice")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)
        self.setAccessibleName("%s. %s" % (title, description))

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 22)
        lay.setSpacing(8)

        bubble = QtWidgets.QLabel()
        bubble.setFixedSize(48, 48)
        bubble.setAlignment(QtCore.Qt.AlignCenter)
        bubble.setStyleSheet("background: %s; border-radius: 12px;" % theme.ACCENT_SOFT)
        bubble.setPixmap(theme.icon_pixmap(icon_name, 24, theme.ACCENT))
        lay.addWidget(bubble)
        lay.addSpacing(8)

        t = theme.label(title, "stepTitle")
        t.setStyleSheet("font-size: 18px;")
        lay.addWidget(t)
        d = theme.label(description, "hint", wrap=True)
        lay.addWidget(d)
        lay.addStretch()

        cta_row = QtWidgets.QHBoxLayout()
        cta_row.setSpacing(6)
        c = QtWidgets.QLabel(cta)
        c.setStyleSheet("color: %s; font-weight: 600;" % theme.ACCENT)
        cta_row.addWidget(c)
        cta_row.addWidget(theme.icon_label("arrow", 16, theme.ACCENT))
        cta_row.addStretch()
        lay.addLayout(cta_row)

        for child in self.findChildren(QtWidgets.QLabel):
            child.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)


class HomePage(QtWidgets.QWidget):

    hideRequested = QtCore.pyqtSignal()
    revealRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(HomePage, self).__init__(parent)
        self.setObjectName("page")
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 28)
        outer.addStretch(1)
        column_w = QtWidgets.QWidget()
        column_w.setMaximumWidth(760)
        outer.addWidget(column_w, 100)
        outer.addStretch(1)
        col = QtWidgets.QVBoxLayout(column_w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        brand = QtWidgets.QHBoxLayout()
        brand.setSpacing(10)
        logo = QtWidgets.QLabel()
        logo.setFixedSize(34, 34)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setStyleSheet("background: %s; border-radius: 9px;" % theme.ACCENT)
        logo.setPixmap(theme.icon_pixmap("lock", 18, "#ffffff"))
        brand.addWidget(logo)
        brand.addWidget(theme.label("Whisper", "appName"))
        brand.addStretch()
        col.addLayout(brand)
        col.addStretch(2)

        col.addWidget(theme.label("Hide a secret inside a picture or audio file", "hero", wrap=True))
        col.addSpacing(10)
        col.addWidget(theme.label(
            "Your file still looks and sounds exactly the same. Only someone "
            "with the password can read what's inside.", "heroSub", wrap=True))
        col.addSpacing(32)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(16)
        self.hide_card = ChoiceCard(
            "lock", "Hide a message",
            "Put a text message or a picture inside a picture, WAV or MP3 file.",
            "Start hiding")
        self.hide_card.clicked.connect(self.hideRequested)
        cards.addWidget(self.hide_card)
        self.reveal_card = ChoiceCard(
            "search", "Read a hidden message",
            "Open a file made with Whisper and unlock it with the password.",
            "Open a file")
        self.reveal_card.clicked.connect(self.revealRequested)
        cards.addWidget(self.reveal_card)
        col.addLayout(cards)
        col.addSpacing(28)

        # how it works
        steps = QtWidgets.QHBoxLayout()
        steps.setSpacing(20)
        for n, text in ((1, "Pick a picture or audio file"),
                        (2, "Add your secret and a password"),
                        (3, "Save it and share it like any file")):
            item = QtWidgets.QHBoxLayout()
            item.setSpacing(8)
            num = QtWidgets.QLabel(str(n))
            num.setObjectName("stepNum")
            num.setFixedSize(24, 24)
            num.setAlignment(QtCore.Qt.AlignCenter)
            num.setStyleSheet("border-radius: 12px; font-size: 12px;")
            item.addWidget(num)
            item.addWidget(theme.label(text, "hint"))
            steps.addLayout(item)
            if n < 3:
                steps.addStretch()
        col.addLayout(steps)
        col.addStretch(3)

        col.addWidget(theme.label(
            "Secrets are encrypted with AES-256-GCM and a scrypt-derived key. "
            "Hiding is not invisibility: statistical analysis can still tell that "
            "a file was changed. See SECURITY.md.", "faint", wrap=True))


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setObjectName("StartWindow")
        MainWindow.setWindowTitle("Whisper")
        MainWindow.resize(900, 780)
        MainWindow.setMinimumSize(720, 600)

        self.stack = QtWidgets.QStackedWidget()
        MainWindow.setCentralWidget(self.stack)

        self.home = HomePage()
        self.home.hideRequested.connect(self.openHideMessageWindow)
        self.home.revealRequested.connect(self.openRevealContentWindow)
        self.stack.addWidget(self.home)
        self.hide_page = None
        self.reveal_page = None

        self.home.hide_card.setFocus()

    def goHome(self):
        self.MainWindow.setWindowTitle("Whisper")
        self.stack.setCurrentWidget(self.home)

    def openHideMessageWindow(self):
        if self.hide_page is None:
            from gui.HideMessage.hideMessage import HidePage
            self.hide_page = HidePage(on_back=self.goHome)
            self.stack.addWidget(self.hide_page)
        self.MainWindow.setWindowTitle("Whisper — Hide a message")
        self.stack.setCurrentWidget(self.hide_page)

    def openRevealContentWindow(self):
        if self.reveal_page is None:
            from gui.RevealContent.revealContent import RevealPage
            self.reveal_page = RevealPage(on_back=self.goHome)
            self.stack.addWidget(self.reveal_page)
        self.MainWindow.setWindowTitle("Whisper — Read a hidden message")
        self.stack.setCurrentWidget(self.reveal_page)

    def retranslateUi(self, MainWindow):
        pass


def _excepthook(exc_type, exc, tb):
    """Show unhandled errors instead of letting PyQt5 abort silently.

    Since PyQt 5.5, an exception escaping a slot (e.g. a button handler)
    calls qFatal() and kills the process with no traceback on Windows.
    """
    import traceback
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    sys.stderr.write(text)
    if QtWidgets.QApplication.instance() is not None:
        box = QtWidgets.QMessageBox()
        box.setIcon(QtWidgets.QMessageBox.Critical)
        box.setWindowTitle("Whisper — error")
        box.setText("%s: %s" % (exc_type.__name__, exc))
        box.setDetailedText(text)
        box.exec_()


def main():
    sys.excepthook = _excepthook
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Whisper")
    theme.apply(app)
    app.setWindowIcon(theme.icon("lock", 64, theme.ACCENT))
    window = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
