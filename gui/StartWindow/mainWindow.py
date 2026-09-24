"""The start window: choose an operation.

Rewritten alongside the other two. The generated version painted a script
logo and two rounded cards with a custom hover animation, none of which
matched what the app does, and it carried a real bug: the Hide handler
closed a module-level global named MainWindow, which only exists when
this file is run directly. Imported any other way, clicking Hide raised
NameError after opening the window.

This window is the app's front door, so it states the two operations
plainly and in the same visual language as the windows they lead to.
"""

import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import gui  # sets sys.path for both the GUI and the engine

from gui import theme


class OperationButton(QtWidgets.QPushButton):
    """One of the two choices: a glyph, a name and a line of explanation.

    A QPushButton subclass rather than a composed widget so it keeps the
    real button's keyboard handling, focus ring and accessible role for
    free -- the previous version was a QWidget with a mousePressEvent,
    which the keyboard could not reach at all.
    """

    def __init__(self, glyph, title, description, parent=None):
        super(OperationButton, self).__init__(parent)
        self.glyph = glyph
        self.title = title
        self.description = description
        self.setObjectName("launch")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMinimumHeight(96)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)
        # The text is painted below, but the accessible name has to come
        # from somewhere a screen reader can read.
        self.setAccessibleName("%s. %s" % (title, description))

    def paintEvent(self, event):
        super(OperationButton, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        lit = self.underMouse() or self.hasFocus()
        left = 26

        painter.setFont(theme.mono(22, QtGui.QFont.Bold))
        painter.setPen(QtGui.QColor(theme.SIGNAL))
        painter.drawText(left, int(self.height() / 2) + 8, self.glyph)
        glyph_width = painter.fontMetrics().width(self.glyph)

        text_x = left + glyph_width + 22
        font = QtGui.QFont("Segoe UI", 12)
        font.setWeight(QtGui.QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#ffffff" if lit else theme.TEXT))
        painter.drawText(text_x, int(self.height() / 2) - 4, self.title)

        painter.setFont(theme.mono(11))
        painter.setPen(QtGui.QColor(theme.TEXT_DIM))
        painter.drawText(text_x, int(self.height() / 2) + 18, self.description)

        # A short accent rail on the left edge marks the hovered choice
        # with something other than colour alone.
        if lit:
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(theme.SIGNAL))
            painter.drawRect(0, 0, 3, self.height())


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setObjectName("StartWindow")
        MainWindow.setWindowTitle("Whisper")
        MainWindow.resize(640, 560)
        MainWindow.setMinimumSize(520, 460)

        central = QtWidgets.QWidget()
        MainWindow.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 32)
        layout.setSpacing(0)

        eyebrow = QtWidgets.QLabel("WHISPER  //  STEGANOGRAPHY")
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        layout.addSpacing(10)

        headline = QtWidgets.QLabel("Hide information in plain files")
        headline.setObjectName("headline")
        layout.addWidget(headline)
        layout.addSpacing(6)

        subhead = QtWidgets.QLabel(
            "Whisper writes a payload into a PNG image or an MP3 file and "
            "locks it behind a key. The carrier still opens normally "
            "everywhere else.")
        subhead.setObjectName("subhead")
        subhead.setWordWrap(True)
        layout.addWidget(subhead)
        layout.addSpacing(28)

        self.convertButton = OperationButton(
            "[+]", "Hide Content",
            "Put text or an image inside a carrier file")
        self.convertButton.clicked.connect(self.openHideMessageWindow)
        layout.addWidget(self.convertButton)
        layout.addSpacing(12)

        self.checkButton = OperationButton(
            "[>]", "Reveal Content",
            "Recover what is hidden in a file you already have")
        self.checkButton.clicked.connect(self.openRevealContentWindow)
        layout.addWidget(self.checkButton)

        layout.addStretch()

        footer = QtWidgets.QLabel(
            "Whisper hides data and locks it with a key. Treat it as "
            "concealment, not as a guarantee of secrecy.")
        footer.setObjectName("note")
        footer.setWordWrap(True)
        layout.addWidget(footer)

        self.convertButton.setFocus()

    def openHideMessageWindow(self):
        from gui.HideMessage.hideMessage import Ui_MainWindow as HideMessageUI
        self.hide_message_window = QtWidgets.QMainWindow()
        self.ui_hide_message = HideMessageUI()
        self.ui_hide_message.setupUi(self.hide_message_window)
        self.hide_message_window.show()
        # self.MainWindow, not a module-level global: the old code closed a
        # name that only existed when this file was run directly.
        self.MainWindow.close()

    def openRevealContentWindow(self):
        from gui.RevealContent.revealContent import Ui_MainWindow as RevealContentUI
        self.reveal_window = QtWidgets.QMainWindow()
        self.ui_reveal = RevealContentUI()
        self.ui_reveal.setupUi(self.reveal_window)
        self.reveal_window.show()
        self.MainWindow.close()

    def retranslateUi(self, MainWindow):
        """Kept for compatibility with the generated-code call pattern."""
        pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    theme.apply(app)
    window = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(window)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
