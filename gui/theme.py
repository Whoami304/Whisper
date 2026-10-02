"""Whisper visual theme: a light, friendly UI with plain-language widgets.

Everything visual lives here so the pages only describe *what* they show:
colours, the stylesheet, painted icons, and a handful of reusable widgets
(step cards, a drop zone, a file card, a segmented switch, a usage bar and
a status banner).
"""

from PyQt5 import QtCore, QtGui, QtWidgets

# --- palette ----------------------------------------------------------

BG = "#f5f6fa"
SURFACE = "#ffffff"
SURFACE_ALT = "#f8f9fc"
BORDER = "#e4e7ee"
BORDER_STRONG = "#cfd5e1"

TEXT = "#1c2130"
TEXT_DIM = "#5d6578"
TEXT_FAINT = "#8f97a8"

ACCENT = "#4f5bd5"
ACCENT_HOVER = "#4350c4"
ACCENT_PRESSED = "#3943a8"
ACCENT_SOFT = "#eef0fc"
ACCENT_SOFT_BORDER = "#c9cdf4"

SUCCESS = "#15803d"
SUCCESS_SOFT = "#e9f7ee"
WARN = "#b45309"
WARN_SOFT = "#fdf5e6"
DANGER = "#c62828"
DANGER_SOFT = "#fdeeee"

SANS_STACK = '"Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", sans-serif'
SANS_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue"]


def font(size=13, weight=QtGui.QFont.Normal):
    """A UI QFont for painted widgets, using the first family installed."""
    f = QtGui.QFont()
    for family in SANS_FAMILIES:
        f.setFamily(family)
        if QtGui.QFontInfo(f).family().lower() == family.lower():
            break
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def human_bytes(count):
    """Friendly byte count string."""
    if count < 1024:
        return "%d bytes" % count
    if count < 1024 * 1024:
        return "%.0f KB" % (count / 1024.0) if count >= 10 * 1024 else "%.1f KB" % (count / 1024.0)
    return "%.1f MB" % (count / (1024.0 * 1024.0))


# --- stylesheet -------------------------------------------------------


def stylesheet():
    return """
    QWidget {
        color: %(text)s;
        font-family: %(sans)s;
        font-size: 14px;
    }
    QMainWindow, QWidget#page, QWidget#canvas { background: %(bg)s; }
    QLabel { background: transparent; }
    QToolTip {
        background: %(text)s; color: #ffffff; border: none;
        border-radius: 6px; padding: 6px 9px; font-size: 12px;
    }

    /* --- type --- */
    QLabel#appName  { font-size: 18px; font-weight: 700; }
    QLabel#hero     { font-size: 28px; font-weight: 700; }
    QLabel#heroSub  { font-size: 15px; color: %(text_dim)s; }
    QLabel#pageTitle { font-size: 17px; font-weight: 600; }
    QLabel#stepTitle { font-size: 16px; font-weight: 600; }
    QLabel#stepHint  { font-size: 13px; color: %(text_dim)s; }
    QLabel#fieldLabel { font-size: 13px; font-weight: 600; color: %(text)s; }
    QLabel#hint     { font-size: 13px; color: %(text_dim)s; }
    QLabel#faint    { font-size: 12px; color: %(text_faint)s; }
    QLabel#fileName { font-size: 14px; font-weight: 600; }
    QLabel#stepNum {
        background: %(accent_soft)s; color: %(accent)s;
        border-radius: 14px; font-size: 13px; font-weight: 700;
    }
    QLabel#stepNum[done="true"] { background: %(success_soft)s; color: %(success)s; }

    /* --- surfaces --- */
    QFrame#card {
        background: %(surface)s;
        border: 1px solid %(border)s;
        border-radius: 14px;
    }
    QFrame#topBar, QFrame#actionBar { background: %(surface)s; }
    QFrame#topBar   { border-bottom: 1px solid %(border)s; }
    QFrame#actionBar { border-top: 1px solid %(border)s; }
    QFrame#fileCard {
        background: %(surface_alt)s;
        border: 1px solid %(border)s;
        border-radius: 12px;
    }
    QLabel#thumb {
        background: %(accent_soft)s;
        border-radius: 8px;
    }

    /* --- inputs --- */
    QLineEdit, QPlainTextEdit, QTextEdit {
        background: %(surface)s;
        color: %(text)s;
        border: 1px solid %(border_strong)s;
        border-radius: 10px;
        padding: 9px 12px;
        font-size: 14px;
        selection-background-color: %(accent)s;
        selection-color: #ffffff;
    }
    QLineEdit:hover, QPlainTextEdit:hover { border-color: #b8c0d0; }
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
        border: 2px solid %(accent)s;
        padding: 8px 11px;
    }
    QPlainTextEdit[readOnly="true"] { background: %(surface_alt)s; }

    QComboBox {
        background: %(surface)s;
        border: 1px solid %(border_strong)s;
        border-radius: 10px;
        padding: 8px 12px;
        min-height: 22px;
        font-size: 14px;
    }
    QComboBox:hover { border-color: #b8c0d0; }
    QComboBox:focus { border: 2px solid %(accent)s; padding: 7px 11px; }
    QComboBox::drop-down { border: none; width: 28px; }
    QComboBox::down-arrow {
        image: url(%(chevron)s);
        width: 12px; height: 12px;
        margin-right: 10px;
    }
    QComboBox QAbstractItemView {
        background: %(surface)s;
        border: 1px solid %(border)s;
        border-radius: 8px;
        padding: 4px;
        outline: none;
        selection-background-color: %(accent_soft)s;
        selection-color: %(text)s;
    }

    /* --- buttons --- */
    QPushButton {
        background: %(surface)s;
        color: %(text)s;
        border: 1px solid %(border_strong)s;
        border-radius: 10px;
        padding: 9px 16px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover { background: %(surface_alt)s; border-color: #b8c0d0; }
    QPushButton:pressed { background: #eef0f5; }
    QPushButton:focus { border: 2px solid %(accent)s; padding: 8px 15px; }
    QPushButton:disabled { color: %(text_faint)s; background: %(surface_alt)s; border-color: %(border)s; }

    QPushButton#primary {
        background: %(accent)s;
        color: #ffffff;
        border: none;
        font-weight: 600;
        padding: 11px 24px;
        font-size: 15px;
    }
    QPushButton#primary:hover { background: %(accent_hover)s; }
    QPushButton#primary:pressed { background: %(accent_pressed)s; }
    QPushButton#primary:focus { border: 2px solid %(accent_soft_border)s; padding: 9px 22px; }
    QPushButton#primary:disabled { background: #b9bfe9; color: #ffffff; }

    QPushButton#ghost {
        background: transparent;
        border: none;
        color: %(text_dim)s;
        padding: 8px 12px;
        font-weight: 500;
    }
    QPushButton#ghost:hover { background: #eceef4; color: %(text)s; }
    QPushButton#ghost:focus { border: 2px solid %(accent)s; padding: 6px 10px; }

    QPushButton#link {
        background: transparent;
        border: none;
        color: %(accent)s;
        padding: 6px 8px;
        font-weight: 600;
    }
    QPushButton#link:hover { color: %(accent_hover)s; text-decoration: underline; }

    /* --- segmented switch --- */
    QFrame#segment {
        background: #eceef4;
        border-radius: 11px;
    }
    QPushButton#segBtn {
        background: transparent;
        border: none;
        border-radius: 8px;
        color: %(text_dim)s;
        padding: 8px 18px;
        font-weight: 600;
    }
    QPushButton#segBtn:hover { color: %(text)s; }
    QPushButton#segBtn:checked {
        background: %(surface)s;
        color: %(text)s;
        border: 1px solid %(border)s;
    }
    QPushButton#segBtn:disabled { color: %(text_faint)s; }

    /* --- home choice cards --- */
    QPushButton#choice {
        background: %(surface)s;
        border: 1px solid %(border)s;
        border-radius: 16px;
        padding: 0;
        text-align: left;
    }
    QPushButton#choice:hover { border: 2px solid %(accent)s; }
    QPushButton#choice:focus { border: 2px solid %(accent)s; }

    /* --- scrollbars --- */
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
    QScrollBar::handle:vertical { background: #cdd2dc; border-radius: 3px; min-height: 30px; }
    QScrollBar::handle:vertical:hover { background: #aab1bf; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none; border: none; height: 0;
    }
    QMessageBox { background: %(surface)s; }
    """ % {
        "bg": BG, "surface": SURFACE, "surface_alt": SURFACE_ALT,
        "border": BORDER, "border_strong": BORDER_STRONG,
        "text": TEXT, "text_dim": TEXT_DIM, "text_faint": TEXT_FAINT,
        "accent": ACCENT, "accent_hover": ACCENT_HOVER,
        "accent_pressed": ACCENT_PRESSED, "accent_soft": ACCENT_SOFT,
        "accent_soft_border": ACCENT_SOFT_BORDER,
        "success": SUCCESS, "success_soft": SUCCESS_SOFT,
        "sans": SANS_STACK,
        "chevron": _chevron_path(),
    }


def _chevron_path():
    """Writes a small chevron PNG for the combo box arrow; QSS needs a file."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "whisper_chevron.png")
    if not os.path.exists(path):
        pm = QtGui.QPixmap(24, 24)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor(TEXT_DIM), 2.6)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(6, 9), QtCore.QPointF(12, 15),
                                        QtCore.QPointF(18, 9)]))
        p.end()
        pm.save(path)
    return path.replace("\\", "/")


def apply(app):
    """Applies the palette and stylesheet to a QApplication."""
    app.setStyle("Fusion")
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(BG))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(SURFACE))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(SURFACE_ALT))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(SURFACE))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(ACCENT))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(TEXT_FAINT))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("#ffffff"))
    app.setPalette(palette)
    app.setFont(font(14))
    app.setStyleSheet(stylesheet())


# --- painted icons ----------------------------------------------------


def _draw_icon(p, name, s):
    """Draws a line icon `name` into a square of side s."""
    def pt(x, y):
        return QtCore.QPointF(x * s, y * s)

    if name in ("lock", "unlock"):
        p.drawRoundedRect(QtCore.QRectF(pt(0.20, 0.45), pt(0.80, 0.88)), s * 0.08, s * 0.08)
        path = QtGui.QPainterPath()
        if name == "lock":
            path.moveTo(pt(0.32, 0.45))
            path.lineTo(pt(0.32, 0.32))
            path.arcTo(QtCore.QRectF(pt(0.32, 0.12), pt(0.68, 0.48)), 180, -180)
            path.lineTo(pt(0.68, 0.45))
        else:
            path.moveTo(pt(0.32, 0.45))
            path.lineTo(pt(0.32, 0.32))
            path.arcTo(QtCore.QRectF(pt(0.32, 0.12), pt(0.68, 0.48)), 180, -150)
        p.drawPath(path)
        p.drawLine(pt(0.5, 0.62), pt(0.5, 0.72))
    elif name == "search":
        p.drawEllipse(QtCore.QRectF(pt(0.16, 0.16), pt(0.66, 0.66)))
        p.drawLine(pt(0.60, 0.60), pt(0.84, 0.84))
    elif name == "upload":
        p.drawLine(pt(0.5, 0.18), pt(0.5, 0.62))
        p.drawPolyline(QtGui.QPolygonF([pt(0.32, 0.36), pt(0.5, 0.18), pt(0.68, 0.36)]))
        p.drawPolyline(QtGui.QPolygonF([pt(0.18, 0.62), pt(0.18, 0.82), pt(0.82, 0.82), pt(0.82, 0.62)]))
    elif name == "image":
        p.drawRoundedRect(QtCore.QRectF(pt(0.14, 0.20), pt(0.86, 0.80)), s * 0.08, s * 0.08)
        p.drawPolyline(QtGui.QPolygonF([pt(0.14, 0.70), pt(0.38, 0.48), pt(0.56, 0.64), pt(0.68, 0.54), pt(0.86, 0.70)]))
        p.drawEllipse(pt(0.64, 0.36), s * 0.06, s * 0.06)
    elif name == "music":
        p.drawLine(pt(0.38, 0.70), pt(0.38, 0.22))
        p.drawLine(pt(0.78, 0.62), pt(0.78, 0.16))
        p.drawLine(pt(0.38, 0.22), pt(0.78, 0.16))
        p.drawEllipse(pt(0.29, 0.72), s * 0.09, s * 0.08)
        p.drawEllipse(pt(0.69, 0.64), s * 0.09, s * 0.08)
    elif name == "text":
        for y, x2 in ((0.26, 0.82), (0.42, 0.82), (0.58, 0.82), (0.74, 0.58)):
            p.drawLine(pt(0.18, y), pt(x2, y))
    elif name == "check":
        p.drawEllipse(QtCore.QRectF(pt(0.10, 0.10), pt(0.90, 0.90)))
        p.drawPolyline(QtGui.QPolygonF([pt(0.32, 0.51), pt(0.45, 0.64), pt(0.69, 0.38)]))
    elif name == "alert":
        path = QtGui.QPainterPath()
        path.moveTo(pt(0.5, 0.12))
        path.lineTo(pt(0.90, 0.84))
        path.lineTo(pt(0.10, 0.84))
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(pt(0.5, 0.40), pt(0.5, 0.60))
        p.drawPoint(pt(0.5, 0.72))
    elif name == "info":
        p.drawEllipse(QtCore.QRectF(pt(0.10, 0.10), pt(0.90, 0.90)))
        p.drawLine(pt(0.5, 0.46), pt(0.5, 0.70))
        p.drawPoint(pt(0.5, 0.32))
    elif name == "back":
        p.drawLine(pt(0.22, 0.5), pt(0.80, 0.5))
        p.drawPolyline(QtGui.QPolygonF([pt(0.44, 0.28), pt(0.22, 0.5), pt(0.44, 0.72)]))
    elif name == "arrow":
        p.drawLine(pt(0.20, 0.5), pt(0.78, 0.5))
        p.drawPolyline(QtGui.QPolygonF([pt(0.56, 0.28), pt(0.78, 0.5), pt(0.56, 0.72)]))
    elif name == "file":
        path = QtGui.QPainterPath()
        path.moveTo(pt(0.24, 0.12))
        path.lineTo(pt(0.58, 0.12))
        path.lineTo(pt(0.78, 0.32))
        path.lineTo(pt(0.78, 0.88))
        path.lineTo(pt(0.24, 0.88))
        path.closeSubpath()
        p.drawPath(path)
        p.drawPolyline(QtGui.QPolygonF([pt(0.58, 0.12), pt(0.58, 0.32), pt(0.78, 0.32)]))


def icon_pixmap(name, size=20, color=TEXT, width=None):
    """A crisp, DPI-aware pixmap of a line icon."""
    app = QtWidgets.QApplication.instance()
    dpr = app.devicePixelRatio() if app else 1.0
    pm = QtGui.QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor(color), width or max(1.5, size / 12.0))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    _draw_icon(p, name, size)
    p.end()
    return pm


def icon(name, size=18, color=TEXT):
    return QtGui.QIcon(icon_pixmap(name, size, color))


def icon_label(name, size=20, color=TEXT):
    label = QtWidgets.QLabel()
    label.setPixmap(icon_pixmap(name, size, color))
    label.setFixedSize(size, size)
    return label


# --- reusable widgets -------------------------------------------------


def label(text, name=None, wrap=False):
    w = QtWidgets.QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


class StepCard(QtWidgets.QFrame):
    """A white card with a numbered circle, a title and a one-line hint."""

    def __init__(self, number, title, hint="", parent=None):
        super(StepCard, self).__init__(parent)
        self.setObjectName("card")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 22)
        outer.setSpacing(14)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(12)
        self.num = QtWidgets.QLabel(str(number))
        self.num.setObjectName("stepNum")
        self.num.setFixedSize(28, 28)
        self.num.setAlignment(QtCore.Qt.AlignCenter)
        head.addWidget(self.num, 0, QtCore.Qt.AlignTop)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(title, "stepTitle"))
        if hint:
            text.addWidget(label(hint, "stepHint", wrap=True))
        head.addLayout(text, 1)
        outer.addLayout(head)

        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(12)
        outer.addLayout(self.body)
        self._number = str(number)

    def set_done(self, done):
        """Turns the number into a green check once the step is complete."""
        self.num.setProperty("done", "true" if done else "false")
        self.num.setText("✓" if done else self._number)
        self.num.style().unpolish(self.num)
        self.num.style().polish(self.num)


class DropZone(QtWidgets.QFrame):
    """A dashed area that accepts a dropped file or opens a file dialog."""

    fileChosen = QtCore.pyqtSignal(str)

    def __init__(self, title, subtitle, dialog_title, file_filter,
                 icon_name="upload", height=150, parent=None):
        super(DropZone, self).__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.dialog_title = dialog_title
        self.file_filter = file_filter
        self.icon_name = icon_name
        self._hover = False
        self._dragging = False
        self.setAcceptDrops(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMinimumHeight(height)
        self.setAccessibleName("%s. %s" % (title, subtitle))

    def open_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window(), self.dialog_title, "", self.file_filter)
        if path:
            self.fileChosen.emit(path)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.open_dialog()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space):
            self.open_dialog()
        else:
            super(DropZone, self).keyPressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._dragging = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._dragging = False
        self.update()

    def dropEvent(self, event):
        self._dragging = False
        self.update()
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile():
            self.fileChosen.emit(urls[0].toLocalFile())

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        active = self._hover or self._dragging or self.hasFocus()
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(QtGui.QColor(ACCENT_SOFT if active else SURFACE_ALT))
        pen = QtGui.QPen(QtGui.QColor(ACCENT if active else BORDER_STRONG), 1.5)
        pen.setStyle(QtCore.Qt.DashLine)
        pen.setDashPattern([5, 4])
        p.setPen(pen)
        p.drawRoundedRect(rect, 12, 12)

        cy = self.height() / 2.0
        # icon bubble
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(SURFACE))
        p.drawEllipse(QtCore.QPointF(self.width() / 2.0, cy - 26), 22, 22)
        pm = icon_pixmap(self.icon_name, 22, ACCENT)
        p.drawPixmap(int(self.width() / 2.0 - 11), int(cy - 37), pm)

        p.setPen(QtGui.QColor(TEXT))
        p.setFont(font(14, QtGui.QFont.DemiBold))
        p.drawText(QtCore.QRectF(0, cy + 4, self.width(), 22),
                   QtCore.Qt.AlignCenter, self.title)
        p.setPen(QtGui.QColor(TEXT_DIM))
        p.setFont(font(13))
        p.drawText(QtCore.QRectF(0, cy + 26, self.width(), 20),
                   QtCore.Qt.AlignCenter, self.subtitle)


class FileCard(QtWidgets.QFrame):
    """Shows a chosen file: thumbnail, name, details, a badge and Change."""

    changeRequested = QtCore.pyqtSignal()
    removeRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(FileCard, self).__init__(parent)
        self.setObjectName("fileCard")
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(14)

        self.thumb = QtWidgets.QLabel()
        self.thumb.setObjectName("thumb")
        self.thumb.setFixedSize(56, 56)
        self.thumb.setAlignment(QtCore.Qt.AlignCenter)
        row.addWidget(self.thumb)

        text = QtWidgets.QVBoxLayout()
        text.setSpacing(3)
        self.name = label("", "fileName")
        self.name.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.details = label("", "hint")
        self.badge = QtWidgets.QLabel()
        self.badge.hide()
        text.addStretch()
        text.addWidget(self.name)
        text.addWidget(self.details)
        text.addWidget(self.badge, 0, QtCore.Qt.AlignLeft)
        text.addStretch()
        row.addLayout(text, 1)

        change = QtWidgets.QPushButton("Change")
        change.clicked.connect(self.changeRequested)
        row.addWidget(change)
        remove = QtWidgets.QPushButton("Remove")
        remove.setObjectName("ghost")
        remove.clicked.connect(self.removeRequested)
        row.addWidget(remove)

    def set_file(self, name, details, thumb_path=None, icon_name="file"):
        self.name.setText(name)
        self.name.setToolTip(name)
        self.details.setText(details)
        pm = None
        if thumb_path:
            pm = QtGui.QPixmap(thumb_path)
            if pm.isNull():
                pm = None
        if pm is not None:
            pm = pm.scaled(56, 56, QtCore.Qt.KeepAspectRatioByExpanding,
                           QtCore.Qt.SmoothTransformation)
            # centre-crop to a square with rounded corners
            out = QtGui.QPixmap(56, 56)
            out.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(out)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(QtCore.QRectF(0, 0, 56, 56), 8, 8)
            painter.setClipPath(clip)
            painter.drawPixmap(int((56 - pm.width()) / 2), int((56 - pm.height()) / 2), pm)
            painter.end()
            self.thumb.setPixmap(out)
        else:
            self.thumb.setPixmap(icon_pixmap(icon_name, 26, ACCENT))

    def set_badge(self, text, kind="neutral"):
        if not text:
            self.badge.hide()
            return
        fg, bg = {
            "success": (SUCCESS, SUCCESS_SOFT),
            "warn": (WARN, WARN_SOFT),
            "danger": (DANGER, DANGER_SOFT),
        }.get(kind, (TEXT_DIM, "#eceef4"))
        self.badge.setText(text)
        self.badge.setStyleSheet(
            "color: %s; background: %s; border-radius: 9px; padding: 2px 9px;"
            "font-size: 12px; font-weight: 600;" % (fg, bg))
        self.badge.show()


class FilePicker(QtWidgets.QWidget):
    """A DropZone that turns into a FileCard once a file is chosen."""

    fileChanged = QtCore.pyqtSignal(str)  # "" when cleared

    def __init__(self, title, subtitle, dialog_title, file_filter,
                 icon_name="upload", height=150, parent=None):
        super(FilePicker, self).__init__(parent)
        self.path = ""
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.zone = DropZone(title, subtitle, dialog_title, file_filter,
                             icon_name, height)
        self.zone.fileChosen.connect(self.set_path)
        lay.addWidget(self.zone)
        self.card = FileCard()
        self.card.changeRequested.connect(self.zone.open_dialog)
        self.card.removeRequested.connect(lambda: self.set_path(""))
        self.card.hide()
        lay.addWidget(self.card)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile():
            self.set_path(urls[0].toLocalFile())

    def set_path(self, path):
        import os
        self.path = os.path.abspath(path) if path else ""
        self.zone.setVisible(not self.path)
        self.card.setVisible(bool(self.path))
        self.fileChanged.emit(self.path)


class Segmented(QtWidgets.QFrame):
    """A pill-shaped switch between a few options."""

    changed = QtCore.pyqtSignal(int)

    def __init__(self, options, parent=None):
        super(Segmented, self).__init__(parent)
        self.setObjectName("segment")
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for index, (text, icon_name) in enumerate(options):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            if icon_name:
                btn.setIcon(icon(icon_name, 16, TEXT_DIM))
            self.group.addButton(btn, index)
            row.addWidget(btn)
            self.buttons.append(btn)
        self.buttons[0].setChecked(True)
        self.group.buttonClicked.connect(
            lambda b: self.changed.emit(self.group.id(b)))
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Fixed)

    def index(self):
        return self.group.checkedId()

    def set_index(self, index):
        self.buttons[index].setChecked(True)
        self.changed.emit(index)


class UsageBar(QtWidgets.QWidget):
    """A smooth, rounded fill bar for 'how much space does this use'."""

    def __init__(self, parent=None):
        super(UsageBar, self).__init__(parent)
        self._ratio = 0.0
        self._known = False
        self.setFixedHeight(8)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)

    def set_unknown(self):
        self._known = False
        self._ratio = 0.0
        self.update()

    def set_ratio(self, ratio):
        self._known = True
        self._ratio = max(0.0, float(ratio))
        self.update()

    def colour(self):
        if self._ratio > 1.0:
            return DANGER
        if self._ratio > 0.85:
            return WARN
        return ACCENT

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.height() / 2.0
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor("#e8ebf1"))
        p.drawRoundedRect(QtCore.QRectF(self.rect()), r, r)
        if self._known and self._ratio > 0:
            w = max(self.height(), self.width() * min(self._ratio, 1.0))
            p.setBrush(QtGui.QColor(self.colour()))
            p.drawRoundedRect(QtCore.QRectF(0, 0, w, self.height()), r, r)


class Banner(QtWidgets.QFrame):
    """A soft coloured message strip with an icon and optional action."""

    KINDS = {
        "info": ("info", ACCENT, ACCENT_SOFT),
        "success": ("check", SUCCESS, SUCCESS_SOFT),
        "warn": ("alert", WARN, WARN_SOFT),
        "error": ("alert", DANGER, DANGER_SOFT),
        "busy": ("info", ACCENT, ACCENT_SOFT),
    }

    def __init__(self, parent=None):
        super(Banner, self).__init__(parent)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(12, 9, 10, 9)
        row.setSpacing(10)
        self.icon = QtWidgets.QLabel()
        self.icon.setFixedSize(18, 18)
        row.addWidget(self.icon, 0, QtCore.Qt.AlignTop)
        self.text = QtWidgets.QLabel()
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        row.addWidget(self.text, 1)
        self.action = QtWidgets.QPushButton()
        self.action.setObjectName("link")
        self.action.hide()
        row.addWidget(self.action, 0, QtCore.Qt.AlignVCenter)
        self._action_cb = None
        self.action.clicked.connect(self._run_action)
        self.hide()

    def _run_action(self):
        if self._action_cb:
            self._action_cb()

    def show_message(self, kind, text, action_text=None, action=None):
        icon_name, fg, bg = self.KINDS.get(kind, self.KINDS["info"])
        self.setStyleSheet(
            "Banner { background: %s; border-radius: 10px; }"
            "QLabel { color: %s; font-size: 13px; }" % (bg, TEXT))
        self.icon.setPixmap(icon_pixmap(icon_name, 18, fg))
        self.text.setText(text)
        self._action_cb = action
        if action_text and action:
            self.action.setText(action_text)
            self.action.show()
        else:
            self.action.hide()
        self.show()

    def clear(self):
        self.hide()


# --- page scaffolding -------------------------------------------------


class Page(QtWidgets.QWidget):
    """A page with a top bar (back + title), a scrolling centred column,
    and a fixed action bar at the bottom."""

    def __init__(self, title, on_back=None, parent=None):
        super(Page, self).__init__(parent)
        self.setObjectName("page")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QtWidgets.QFrame()
        top.setObjectName("topBar")
        top_row = QtWidgets.QHBoxLayout(top)
        top_row.setContentsMargins(16, 10, 24, 10)
        top_row.setSpacing(8)
        self.back_btn = QtWidgets.QPushButton("Home")
        self.back_btn.setObjectName("ghost")
        self.back_btn.setIcon(icon("back", 16, TEXT_DIM))
        self.back_btn.setCursor(QtCore.Qt.PointingHandCursor)
        if on_back:
            self.back_btn.clicked.connect(on_back)
        else:
            self.back_btn.hide()
        top_row.addWidget(self.back_btn)
        sep = QtWidgets.QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: %s;" % BORDER)
        sep.setVisible(bool(on_back))
        top_row.addWidget(sep)
        top_row.addSpacing(6)
        top_row.addWidget(label(title, "pageTitle"))
        top_row.addStretch()
        outer.addWidget(top)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        canvas = QtWidgets.QWidget()
        canvas.setObjectName("canvas")
        self.scroll.setWidget(canvas)
        centre = QtWidgets.QHBoxLayout(canvas)
        centre.setContentsMargins(24, 24, 24, 24)
        centre.addStretch(1)
        column = QtWidgets.QWidget()
        column.setMaximumWidth(720)
        column.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Preferred)
        centre.addWidget(column, 100)
        centre.addStretch(1)
        self.column = QtWidgets.QVBoxLayout(column)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.setSpacing(16)
        outer.addWidget(self.scroll, 1)

        bar = QtWidgets.QFrame()
        bar.setObjectName("actionBar")
        bar_centre = QtWidgets.QHBoxLayout(bar)
        bar_centre.setContentsMargins(24, 14, 24, 14)
        bar_centre.addStretch(1)
        bar_inner = QtWidgets.QWidget()
        bar_inner.setMaximumWidth(720)
        bar_inner.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                QtWidgets.QSizePolicy.Preferred)
        bar_centre.addWidget(bar_inner, 100)
        bar_centre.addStretch(1)
        self.actions = QtWidgets.QHBoxLayout(bar_inner)
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(12)
        outer.addWidget(bar)

    def scroll_to(self, widget):
        QtCore.QTimer.singleShot(
            50, lambda: self.scroll.ensureWidgetVisible(widget, 0, 24))


def field(label_text, widget_or_layout, hint=None):
    """A labelled form field. Returns a QVBoxLayout."""
    box = QtWidgets.QVBoxLayout()
    box.setSpacing(6)
    box.addWidget(label(label_text, "fieldLabel"))
    if isinstance(widget_or_layout, QtWidgets.QLayout):
        box.addLayout(widget_or_layout)
    else:
        box.addWidget(widget_or_layout)
    if hint is not None:
        h = hint if isinstance(hint, QtWidgets.QLabel) else label(hint, "hint", wrap=True)
        box.addWidget(h)
    return box


class PasswordField(QtWidgets.QWidget):
    """A password line edit with a Show/Hide toggle."""

    def __init__(self, placeholder, parent=None):
        super(PasswordField, self).__init__(parent)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.edit = QtWidgets.QLineEdit()
        self.edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.edit.setPlaceholderText(placeholder)
        row.addWidget(self.edit, 1)
        self.toggle = QtWidgets.QPushButton("Show")
        self.toggle.setCheckable(True)
        self.toggle.setFixedWidth(76)
        self.toggle.toggled.connect(self._toggle)
        row.addWidget(self.toggle)
        self.row = row

    def _toggle(self, shown):
        self.edit.setEchoMode(QtWidgets.QLineEdit.Normal if shown
                              else QtWidgets.QLineEdit.Password)
        self.toggle.setText("Hide" if shown else "Show")

    def text(self):
        return self.edit.text()

    def setText(self, text):
        self.edit.setText(text)
