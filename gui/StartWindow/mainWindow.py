"""Whisper's main window: a home screen plus the Hide and Read pages.

Everything lives in one window with a QStackedWidget, so moving between
screens doesn't close and reopen windows (which made the window jump
around and lose its size). The window remembers its size and position.
"""

import os
import sys

if __package__ in (None, ""):          # started as a script, e.g. from PyCharm
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import gui  # sets sys.path and checks/repairs dependencies -- keep before PyQt5

from PyQt5 import QtCore, QtGui, QtWidgets

from gui import theme


class ChoiceCard(QtWidgets.QAbstractButton):
    """A large clickable card on the home screen, fully painted.

    Hover lifts the card (a soft shadow grows under it), tints its border,
    fills the icon tile with the accent colour and nudges the arrow. All of
    it is animated. A mouse click never gives the card keyboard focus, so
    no outline is ever left behind on a card the pointer has moved away from.
    """

    MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 6, 6, 12     # room for the shadow
    RADIUS = 16

    def __init__(self, icon_name, title, description, cta, parent=None):
        super(ChoiceCard, self).__init__(parent)
        self.icon_name, self.title, self.description, self.cta = icon_name, title, description, cta
        self.setObjectName("choice")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.setMinimumHeight(226)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setAccessibleName("%s. %s" % (title, description))
        self.setToolTip(description)
        self._hover = theme.Tween(self, 200)
        self._press = theme.Tween(self, 90)
        self.pressed.connect(lambda: self._press.to(1.0))
        self.released.connect(lambda: self._press.to(0.0))

    def sizeHint(self):
        return QtCore.QSize(320, 226)

    def _card_rect(self):
        return QtCore.QRectF(self.rect()).adjusted(
            self.MARGIN_X, self.MARGIN_TOP, -self.MARGIN_X, -self.MARGIN_BOTTOM)

    def focus_ring_rect(self):
        return self._card_rect()

    def focus_ring_radius(self):
        return self.RADIUS

    def enterEvent(self, event):
        self._hover.to(1.0)
        super(ChoiceCard, self).enterEvent(event)

    def leaveEvent(self, event):
        self._hover.to(0.0)
        super(ChoiceCard, self).leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.click()
        else:
            super(ChoiceCard, self).keyPressEvent(event)

    def paintEvent(self, event):
        h, pr = self._hover.value, self._press.value
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)

        lift = 3.0 * h - 2.0 * pr
        card = self._card_rect().translated(0, -lift)
        theme.paint_shadow(p, card, self.RADIUS, 0.25 + 0.85 * h - 0.5 * pr)

        bg = theme.mix(theme.SURFACE, theme.ACCENT_SOFT, 0.35 * pr)
        p.setBrush(bg)
        p.setPen(QtGui.QPen(theme.mix(theme.BORDER, theme.ACCENT_SOFT_BORDER if theme.MODE == "light"
                                      else theme.ACCENT, h), 1.2))
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), self.RADIUS, self.RADIUS)

        x, y = card.left() + 24, card.top() + 24
        width = card.width() - 48

        # icon tile: soft accent -> solid accent with a white glyph
        tile = QtCore.QRectF(x, y, 48, 48)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(theme.mix(theme.ACCENT_SOFT, theme.ACCENT, h))
        p.drawRoundedRect(tile, 12, 12)
        glyph = theme.mix(theme.ACCENT_TEXT, QtGui.QColor("#ffffff"), h).name()
        p.drawPixmap(int(tile.left() + 12), int(tile.top() + 12),
                     theme.icon_pixmap(self.icon_name, 24, glyph))

        y = tile.bottom() + 18
        p.setPen(QtGui.QColor(theme.TEXT))
        p.setFont(theme.font(18, QtGui.QFont.DemiBold))
        title_h = p.fontMetrics().height()
        p.drawText(QtCore.QRectF(x, y, width, title_h), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                   self.title)
        y += title_h + 6

        # call to action sits on the bottom edge; the description fills the rest
        p.setFont(theme.font(14, QtGui.QFont.DemiBold))
        cta_y = card.bottom() - 22 - p.fontMetrics().height()

        p.setPen(QtGui.QColor(theme.TEXT_DIM))
        p.setFont(theme.font(13))
        desc_rect = QtCore.QRectF(x, y, width, cta_y - 6 - y)
        p.drawText(desc_rect, QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop,
                   self.description)

        p.setFont(theme.font(14, QtGui.QFont.DemiBold))
        accent = theme.mix(theme.ACCENT_TEXT, theme.ACCENT_HOVER if theme.MODE == "light"
                           else QtGui.QColor("#c3c8fb"), h)
        p.setPen(accent)
        cta_w = p.fontMetrics().horizontalAdvance(self.cta)
        p.drawText(QtCore.QRectF(x, cta_y, cta_w + 2, p.fontMetrics().height()),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.cta)
        arrow_x = x + cta_w + 6 + 4 * h
        p.drawPixmap(int(arrow_x), int(cta_y + (p.fontMetrics().height() - 16) / 2),
                     theme.icon_pixmap("arrow", 16, accent.name()))


class _InsetColumn(object):
    """Adds items to a QVBoxLayout with a horizontal inset (default on)."""

    def __init__(self, layout, inset):
        self.layout, self.inset = layout, inset

    def _wrap(self, item, inset):
        if not inset:
            return item
        box = QtWidgets.QHBoxLayout()
        box.setContentsMargins(self.inset, 0, self.inset, 0)
        if isinstance(item, QtWidgets.QLayout):
            box.addLayout(item)
        else:
            box.addWidget(item)
        return box

    def addWidget(self, widget, inset=True):
        self.layout.addLayout(self._wrap(widget, inset))

    def addLayout(self, layout, inset=True):
        self.layout.addLayout(self._wrap(layout, inset))

    def addSpacing(self, n):
        self.layout.addSpacing(n)

    def addStretch(self, n=0):
        self.layout.addStretch(n)


class HomePage(QtWidgets.QWidget):

    hideRequested = QtCore.pyqtSignal()
    revealRequested = QtCore.pyqtSignal()
    themeToggled = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(HomePage, self).__init__(parent)
        self.setObjectName("page")
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 24)
        outer.addStretch(1)
        column_w = QtWidgets.QWidget()
        column_w.setMaximumWidth(780 + 2 * ChoiceCard.MARGIN_X)
        outer.addWidget(column_w, 100)
        outer.addStretch(1)
        page_col = QtWidgets.QVBoxLayout(column_w)
        page_col.setContentsMargins(0, 0, 0, 0)
        page_col.setSpacing(0)
        # The cards reserve a few pixels on each side for their shadow, so
        # inset everything else by the same amount to keep one left edge.
        col = _InsetColumn(page_col, ChoiceCard.MARGIN_X)

        brand = QtWidgets.QHBoxLayout()
        brand.setSpacing(10)
        logo = QtWidgets.QLabel()
        logo.setFixedSize(34, 34)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setPixmap(theme.icon_pixmap("lock", 18, "#ffffff"))
        theme.themed(lambda: logo.setStyleSheet(
            "background: %s; border-radius: 9px;" % theme.ACCENT), logo)
        brand.addWidget(logo)
        brand.addWidget(theme.label("Whisper", "appName"))
        brand.addStretch()
        self.theme_btn = theme.ThemeButton()
        self.theme_btn.clicked.connect(self.themeToggled)
        brand.addWidget(self.theme_btn)
        col.addLayout(brand)
        col.addStretch(2)

        col.addWidget(theme.label("Hide a secret inside a picture or audio file", "hero", wrap=True))
        col.addSpacing(10)
        col.addWidget(theme.label(
            "Your file still looks and sounds exactly the same. Only someone "
            "with the password can read what's inside.", "heroSub", wrap=True))
        col.addSpacing(26)

        cards = QtWidgets.QHBoxLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(16 - 2 * ChoiceCard.MARGIN_X)
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
        col.addLayout(cards, inset=False)
        col.addSpacing(16)

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
        self.home = None
        self.hide_page = None
        self.reveal_page = None
        self._build_home()

        sc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+L"), MainWindow, self.toggleTheme)
        sc.setContext(QtCore.Qt.WindowShortcut)

    def _build_home(self):
        self.home = HomePage()
        self.home.hideRequested.connect(self.openHideMessageWindow)
        self.home.revealRequested.connect(self.openRevealContentWindow)
        self.stack.addWidget(self.home)
        self.stack.setCurrentWidget(self.home)
        # Park focus on the page itself so no control starts out highlighted.
        self.home.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.home.setFocus()

    def toggleTheme(self):
        """Switch light <-> dark and remember it. Pages are re-styled in
        place, so nothing you typed or picked is lost."""
        theme.switch_theme()

    def goHome(self):
        self.MainWindow.setWindowTitle("Whisper")
        self.stack.setCurrentWidget(self.home)
        self.home.setFocus()

    def openHideMessageWindow(self):
        if self.hide_page is None:
            from gui.HideMessage.hideMessage import HidePage
            self.hide_page = HidePage(on_back=self.goHome)
            self.stack.addWidget(self.hide_page)
        self.MainWindow.setWindowTitle("Whisper — Hide a message")
        self._show_page(self.hide_page)

    def openRevealContentWindow(self):
        if self.reveal_page is None:
            from gui.RevealContent.revealContent import RevealPage
            self.reveal_page = RevealPage(on_back=self.goHome)
            self.stack.addWidget(self.reveal_page)
        self.MainWindow.setWindowTitle("Whisper — Read a hidden message")
        self._show_page(self.reveal_page)

    def _show_page(self, page):
        """Switch to page with nothing focused, so no control starts out
        highlighted; the first Tab then lands on the page's first control."""
        self.stack.setCurrentWidget(page)
        page.setFocusPolicy(QtCore.Qt.ClickFocus)
        page.setFocus(QtCore.Qt.OtherFocusReason)

    def retranslateUi(self, MainWindow):
        pass


class MainWindow(QtWidgets.QMainWindow):
    """The application window: remembers its geometry between runs."""

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        geometry = QtCore.QSettings("Whisper", "Whisper").value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    def showEvent(self, event):
        super(MainWindow, self).showEvent(event)
        theme.apply_titlebar(self)

    def closeEvent(self, event):
        QtCore.QSettings("Whisper", "Whisper").setValue("geometry", self.saveGeometry())
        super(MainWindow, self).closeEvent(event)


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
    theme.set_mode(theme.saved_mode())
    theme.apply(app)
    app.setWindowIcon(theme.app_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
