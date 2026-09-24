"""Whisper's visual language, in one place.

Why this module exists: each of the three windows used to carry its own
colours, typed in at roughly thirty call sites as inline setStyleSheet()
strings. The same grey appeared as #2b2b2b, #2d2d2d and #303030, the two
action buttons on one window used two unrelated fills, and nothing could
be restyled without editing every file. Everything visual now comes from
here, so a change lands everywhere at once.

The look is deliberately a security instrument rather than a converter:
Whisper hides information, and the window should say so before the user
reads a single label.

    cool slate ground, never pure black
    one signal colour (cyan) for state, amber for caution, red for failure
    square-ish edges: 2-3px, not pill-shaped
    outlined modules with a numbered header and a hairline rule
    uppercase monospace micro-labels over monospace data readouts
    depth from rules and borders, not from drop shadows

The type ramp keeps a normal UI face for prose so the app stays readable
and ordinary to use; the monospace is reserved for data -- paths, byte
counts, capacities, log lines -- where digits need to line up and where
it reinforces that these are measurements, not decoration.
"""

from PyQt5 import QtCore, QtGui, QtWidgets

# --- palette ----------------------------------------------------------

INK = "#070a0e"          # the window ground
PANEL = "#0d1217"        # a module
PANEL_DEEP = "#0a0e13"   # a field inset into a module
RULE = "#1b242e"         # module borders and hairlines
RULE_BRIGHT = "#26323d"  # a border that needs to be seen

TEXT = "#ccd6de"
TEXT_DIM = "#8595a2"     # 6.1:1 on a module
TEXT_FAINT = "#72818e"   # 4.7:1 -- the micro-labels are 10px, which counts
                         # as normal text for contrast, not large text

SIGNAL = "#3ddbc0"       # the one accent: state, focus, primary action
SIGNAL_DIM = "#1f7a6c"
CAUTION = "#dda63f"
ALERT = "#e0565f"
OKAY = "#4ec98a"

MONO_STACK = '"Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace'
SANS_STACK = '"Segoe UI", "Segoe UI Variable Text", sans-serif'
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono"]


def mono(size=11, weight=QtGui.QFont.Normal, spacing=0.0):
    """A monospace QFont for the widgets that paint themselves."""
    font = QtGui.QFont()
    for family in MONO_FAMILIES:
        font.setFamily(family)
        if QtGui.QFontInfo(font).family().lower() == family.lower():
            break
    font.setStyleHint(QtGui.QFont.Monospace)
    font.setPixelSize(size)
    font.setWeight(weight)
    if spacing:
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, spacing)
    return font


def human_bytes(count):
    """A byte count in the compact form the readouts use."""
    if count < 1024:
        return "%d B" % count
    if count < 1024 * 1024:
        return "%.1f KB" % (count / 1024.0)
    return "%.2f MB" % (count / (1024.0 * 1024.0))


# --- stylesheet -------------------------------------------------------

def stylesheet():
    """The whole application's QSS.

    Applied once to the QApplication rather than per widget, so a window
    opened later is styled without having to remember to do it.
    """
    return """
    QWidget {
        background: transparent;
        color: %(text)s;
        font-family: %(sans)s;
        font-size: 13px;
    }
    QMainWindow, QDialog, QWidget#canvas, QScrollArea > QWidget > QWidget {
        background: %(ink)s;
    }
    QLabel { background: transparent; }
    QToolTip {
        background: %(panel)s;
        color: %(text)s;
        border: 1px solid %(rule_bright)s;
        padding: 4px 6px;
    }

    /* --- masthead --- */
    QLabel#eyebrow {
        font-family: %(mono)s;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 2.4px;
        color: %(signal)s;
    }
    QLabel#headline {
        font-size: 21px;
        font-weight: 600;
        color: %(text)s;
    }
    QLabel#subhead {
        font-size: 12px;
        color: %(text_dim)s;
    }
    QLabel#stateChip {
        font-family: %(mono)s;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.6px;
        color: %(text_dim)s;
        background: %(panel_deep)s;
        border: 1px solid %(rule_bright)s;
        border-radius: 2px;
        padding: 5px 10px;
    }

    /* --- modules --- */
    QFrame#module {
        background: %(panel)s;
        border: 1px solid %(rule)s;
        border-radius: 3px;
    }

    /* --- labels --- */
    QLabel#microLabel, QLabel#readoutKey {
        font-family: %(mono)s;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.4px;
        color: %(text_faint)s;
    }
    QLabel#readoutValue {
        font-family: %(mono)s;
        font-size: 12px;
        font-weight: 600;
        color: %(text)s;
    }
    QLabel#note {
        font-size: 11px;
        color: %(text_dim)s;
    }
    QLabel#noteCaution {
        font-family: %(mono)s;
        font-size: 11px;
        color: %(caution)s;
    }

    /* --- inputs --- */
    QLineEdit, QPlainTextEdit, QTextEdit {
        font-family: %(mono)s;
        font-size: 12px;
        background: %(panel_deep)s;
        color: %(text)s;
        border: 1px solid %(rule)s;
        border-radius: 2px;
        padding: 7px 9px;
        selection-background-color: %(signal_dim)s;
        selection-color: #ffffff;
    }
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
        border: 1px solid %(signal)s;
    }
    QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {
        color: %(text_faint)s;
        background: #090c10;
    }

    QComboBox {
        font-family: %(mono)s;
        font-size: 12px;
        background: %(panel_deep)s;
        color: %(text)s;
        border: 1px solid %(rule)s;
        border-radius: 2px;
        padding: 6px 9px;
        min-height: 20px;
    }
    QComboBox:hover, QComboBox:focus {
        border: 1px solid %(rule_bright)s;
    }
    QComboBox::drop-down {
        border: none;
        width: 18px;
    }
    QComboBox QAbstractItemView {
        font-family: %(mono)s;
        font-size: 12px;
        background: %(panel)s;
        color: %(text)s;
        border: 1px solid %(rule_bright)s;
        selection-background-color: %(signal_dim)s;
        selection-color: #ffffff;
        outline: none;
    }

    /* --- buttons --- */
    QPushButton {
        font-family: %(mono)s;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.2px;
        background: %(panel_deep)s;
        color: %(text)s;
        border: 1px solid %(rule_bright)s;
        border-radius: 2px;
        padding: 8px 14px;
    }
    QPushButton:hover {
        border: 1px solid %(signal_dim)s;
        color: #ffffff;
    }
    QPushButton:pressed  { background: #060a0d; }
    QPushButton:disabled {
        color: %(text_faint)s;
        border: 1px solid %(rule)s;
        background: #090c10;
    }
    QPushButton#primary {
        background: %(signal)s;
        color: %(ink)s;
        border: 1px solid %(signal)s;
        padding: 10px 20px;
    }
    QPushButton#primary:hover {
        background: #55e8ce;
        border: 1px solid #55e8ce;
        color: %(ink)s;
    }
    QPushButton#primary:disabled {
        background: #14312c;
        border: 1px solid #16322d;
        color: #4c6d66;
    }
    QPushButton#secondary {
        color: %(signal)s;
        border: 1px solid %(signal_dim)s;
        padding: 10px 20px;
    }
    QPushButton#secondary:hover {
        background: %(signal)s;
        color: %(ink)s;
        border: 1px solid %(signal)s;
    }
    QPushButton#secondary:disabled {
        color: #4c6d66;
        border: 1px solid %(rule)s;
    }
    QPushButton#danger:hover {
        color: %(alert)s;
        border: 1px solid %(alert)s;
    }
    QPushButton#ghost {
        background: transparent;
        border: 1px solid transparent;
        color: %(text_dim)s;
        padding: 6px 10px;
    }
    QPushButton#ghost:hover {
        color: %(signal)s;
        border: 1px solid %(rule_bright)s;
    }

    /* The two choices on the start window: big, outlined, equal weight. */
    QPushButton#launch {
        font-family: %(sans)s;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0px;
        text-align: left;
        padding: 20px 24px;
        background: %(panel)s;
        border: 1px solid %(rule)s;
        color: %(text)s;
    }
    QPushButton#launch:hover {
        border: 1px solid %(signal_dim)s;
        background: #101821;
        color: #ffffff;
    }

    /* --- the mode switch --- */
    QRadioButton {
        font-family: %(mono)s;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.2px;
        color: %(text_dim)s;
        background: %(panel_deep)s;
        border: 1px solid %(rule)s;
        border-radius: 2px;
        padding: 7px 16px;
    }
    QRadioButton:hover {
        color: %(text)s;
        border: 1px solid %(rule_bright)s;
    }
    QRadioButton:checked {
        color: %(signal)s;
        border: 1px solid %(signal_dim)s;
        background: rgba(61, 219, 192, 0.07);
    }
    /* A square that fills when checked: the state is carried by shape as
       well as by colour, so it survives a colour-blind reading. */
    QRadioButton::indicator {
        width: 7px;
        height: 7px;
        border: 1px solid %(text_faint)s;
        border-radius: 1px;
        background: transparent;
        margin-right: 7px;
    }
    QRadioButton::indicator:checked {
        border: 1px solid %(signal)s;
        background: %(signal)s;
    }

    /* --- the operation log --- */
    QPlainTextEdit#log {
        font-family: %(mono)s;
        font-size: 11px;
        background: #060809;
        color: %(text_dim)s;
        border: 1px solid %(rule)s;
    }

    /* --- scrollbars --- */
    QScrollArea { border: none; }
    QScrollBar:vertical {
        background: transparent;
        width: 9px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: %(rule_bright)s;
        border-radius: 2px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: %(signal_dim)s; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
        border: none;
        height: 0px;
    }
    """ % {
        "ink": INK, "panel": PANEL, "panel_deep": PANEL_DEEP,
        "rule": RULE, "rule_bright": RULE_BRIGHT,
        "text": TEXT, "text_dim": TEXT_DIM, "text_faint": TEXT_FAINT,
        "signal": SIGNAL, "signal_dim": SIGNAL_DIM,
        "caution": CAUTION, "alert": ALERT,
        "mono": MONO_STACK, "sans": SANS_STACK,
    }


def apply(app):
    """Applies the palette and stylesheet to a QApplication."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(INK))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(PANEL_DEEP))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(PANEL))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(SIGNAL_DIM))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(TEXT_FAINT))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())


# --- painted widgets --------------------------------------------------


class StageHeader(QtWidgets.QWidget):
    """A stage's number and name with a hairline running out to the edge.

    Painted rather than assembled from labels because the rule has to
    begin exactly where the title text ends, and a stylesheet cannot
    measure text.
    """

    def __init__(self, index, title, parent=None):
        super(StageHeader, self).__init__(parent)
        self.index = index
        self.title = title
        self.setFixedHeight(18)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        baseline = int(self.height() / 2 + 4)

        # 12px, a step above the title: the monospace faces slash their
        # zero, and at 11px "05" can be misread as "06".
        painter.setFont(mono(12, QtGui.QFont.Bold, 0.8))
        painter.setPen(QtGui.QColor(SIGNAL))
        painter.drawText(0, baseline, self.index)
        index_width = painter.fontMetrics().width(self.index)

        painter.setFont(mono(11, QtGui.QFont.DemiBold, 2.0))
        painter.setPen(QtGui.QColor(TEXT))
        title_x = index_width + 14
        painter.drawText(title_x, baseline, self.title)
        title_width = painter.fontMetrics().width(self.title)

        rule_x = title_x + title_width + 14
        if rule_x < self.width():
            painter.setPen(QtGui.QColor(RULE))
            y = int(self.height() / 2)
            painter.drawLine(rule_x, y, self.width(), y)


class CapacityMeter(QtWidgets.QWidget):
    """How much of the carrier the payload will take, drawn as cells.

    Segmented rather than a smooth bar on purpose: it is a budget, not
    progress -- nothing is running while it is full. It turns amber as
    the budget tightens and red once the payload cannot fit, so the
    state reads without the number beside it.
    """

    CELLS = 40

    def __init__(self, parent=None):
        super(CapacityMeter, self).__init__(parent)
        self._ratio = 0.0
        self._known = False
        self.setFixedHeight(16)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)

    def set_unknown(self):
        """For a carrier with no fixed budget, such as an ID3 tag."""
        self._known = False
        self._ratio = 0.0
        self.update()

    def set_ratio(self, ratio):
        self._known = True
        self._ratio = max(0.0, float(ratio))
        self.update()

    def colour(self):
        if not self._known:
            return RULE_BRIGHT
        if self._ratio > 1.0:
            return ALERT
        if self._ratio > 0.85:
            return CAUTION
        return SIGNAL

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        width, height = self.width(), self.height()
        if width <= 0:
            return
        gap = 2
        cell = max(1.0, (width - gap * (self.CELLS - 1)) / float(self.CELLS))
        filled = int(round(min(self._ratio, 1.0) * self.CELLS)) if self._known else 0
        # Any payload at all lights one cell, so a small one never looks
        # like nothing at all.
        if self._known and self._ratio > 0 and filled == 0:
            filled = 1

        on = QtGui.QColor(self.colour())
        off = QtGui.QColor(RULE)
        painter.setPen(QtCore.Qt.NoPen)
        for index in range(self.CELLS):
            painter.setBrush(on if index < filled else off)
            painter.drawRect(int(index * (cell + gap)), 0, int(cell), height)


# --- small builders ---------------------------------------------------


def module(index, title):
    """A stage container. Returns (frame, content_layout)."""
    frame = QtWidgets.QFrame()
    frame.setObjectName("module")
    outer = QtWidgets.QVBoxLayout(frame)
    outer.setContentsMargins(16, 13, 16, 15)
    outer.setSpacing(11)
    outer.addWidget(StageHeader(index, title))
    content = QtWidgets.QVBoxLayout()
    content.setContentsMargins(0, 0, 0, 0)
    content.setSpacing(10)
    outer.addLayout(content)
    return frame, content


def micro_label(text):
    label = QtWidgets.QLabel(text)
    label.setObjectName("microLabel")
    return label


def readout(key, initial="--"):
    """A KEY over a value, for the technical metadata rows.

    Returns (layout, value_label) so the caller keeps a handle on the
    part that changes.
    """
    box = QtWidgets.QVBoxLayout()
    box.setSpacing(2)
    key_label = QtWidgets.QLabel(key)
    key_label.setObjectName("readoutKey")
    value_label = QtWidgets.QLabel(initial)
    value_label.setObjectName("readoutValue")
    box.addWidget(key_label)
    box.addWidget(value_label)
    return box, value_label


def state_chip(text="IDLE"):
    chip = QtWidgets.QLabel(text)
    chip.setObjectName("stateChip")
    return chip


def set_chip(chip, text, colour=TEXT_DIM):
    chip.setText(text)
    chip.setStyleSheet("color: %s; border: 1px solid %s;" % (colour, colour))


def masthead(eyebrow_text, headline_text, subhead_text):
    """The window's header. Returns (layout, chip)."""
    box = QtWidgets.QVBoxLayout()
    box.setSpacing(3)
    box.setContentsMargins(0, 0, 0, 6)

    top = QtWidgets.QHBoxLayout()
    top.setSpacing(10)
    eyebrow = QtWidgets.QLabel(eyebrow_text)
    eyebrow.setObjectName("eyebrow")
    top.addWidget(eyebrow)
    top.addStretch()
    chip = state_chip()
    top.addWidget(chip)
    box.addLayout(top)

    headline = QtWidgets.QLabel(headline_text)
    headline.setObjectName("headline")
    box.addWidget(headline)

    subhead = QtWidgets.QLabel(subhead_text)
    subhead.setObjectName("subhead")
    subhead.setWordWrap(True)
    box.addWidget(subhead)
    return box, chip


def scrollable(window, margins=(28, 24, 28, 28), spacing=14):
    """A scrolling page inside `window`. Returns the page's QVBoxLayout.

    Every window scrolls: the stages do not fit a small laptop screen at
    the old fixed 900x700, and the previous windows positioned every
    widget absolutely, so on a shorter screen the lower half was simply
    unreachable.
    """
    central = QtWidgets.QWidget()
    window.setCentralWidget(central)
    outer = QtWidgets.QVBoxLayout(central)
    outer.setContentsMargins(0, 0, 0, 0)

    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QtWidgets.QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    outer.addWidget(area)

    canvas = QtWidgets.QWidget()
    canvas.setObjectName("canvas")
    area.setWidget(canvas)
    page = QtWidgets.QVBoxLayout(canvas)
    page.setContentsMargins(*margins)
    page.setSpacing(spacing)
    return page
