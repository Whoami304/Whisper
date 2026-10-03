"""Whisper visual theme: light and dark palettes and plain-language widgets.

Everything visual lives here so the pages only describe *what* they show:
colours, the stylesheet, painted icons, and a handful of reusable widgets
(step cards, a drop zone, a file card, a segmented switch, a usage bar and
a status banner).

Interaction model
-----------------
* Hover is the mouse's job: surfaces tint and lift smoothly, nothing gets a
  hard outline just because the pointer passed over it.
* Focus is the keyboard's job: buttons, cards and the drop zone never take
  focus from a mouse click, and a focus ring (a soft halo with a small gap,
  like a browser's :focus-visible) appears only while you move with Tab.
  Text fields keep their own accent border, because you type into them.
* The theme can be switched at any time without rebuilding the screens:
  widgets that bake colours into their own style register with themed(),
  and are re-styled when the palette changes.
"""

import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

# --- palettes ---------------------------------------------------------

LIGHT = {
    "BG": "#f5f6fa", "SURFACE": "#ffffff", "SURFACE_ALT": "#f8f9fc",
    "BORDER": "#e4e7ee", "BORDER_STRONG": "#cfd5e1", "BORDER_HOVER": "#b8c0d0",
    "TEXT": "#1c2130", "TEXT_DIM": "#5d6578", "TEXT_FAINT": "#6e7688",
    "ACCENT": "#4f5bd5", "ACCENT_HOVER": "#4350c4", "ACCENT_PRESSED": "#3943a8",
    "ACCENT_TEXT": "#4652d0",
    "ACCENT_SOFT": "#eef0fc", "ACCENT_SOFT_BORDER": "#c9cdf4",
    "SUCCESS": "#15803d", "SUCCESS_SOFT": "#e9f7ee",
    "WARN": "#b45309", "WARN_SOFT": "#fdf5e6",
    "DANGER": "#c62828", "DANGER_SOFT": "#fdeeee",
    "PRESSED": "#eef0f5", "MUTED": "#eceef4", "TRACK": "#e8ebf1",
    "SEG_ACTIVE": "#ffffff",
    "SCROLL": "#cdd2dc", "SCROLL_HOVER": "#aab1bf", "PRIMARY_DISABLED": "#b9bfe9",
    "TOOLTIP_BG": "#1c2130", "TOOLTIP_FG": "#ffffff",
    "SHADOW": "#1c2a5a",
}

DARK = {
    "BG": "#0f1219", "SURFACE": "#171b24", "SURFACE_ALT": "#1d2230",
    "BORDER": "#2a3040", "BORDER_STRONG": "#363d50", "BORDER_HOVER": "#4a5268",
    "TEXT": "#e7e9f0", "TEXT_DIM": "#a3a9b8", "TEXT_FAINT": "#858c9e",
    "ACCENT": "#5b65e3", "ACCENT_HOVER": "#6a74ec", "ACCENT_PRESSED": "#4e57d2",
    "ACCENT_TEXT": "#9aa2f8",
    "ACCENT_SOFT": "#222849", "ACCENT_SOFT_BORDER": "#3d4680",
    "SUCCESS": "#4ade80", "SUCCESS_SOFT": "#13291d",
    "WARN": "#f5a524", "WARN_SOFT": "#2e2312",
    "DANGER": "#f87171", "DANGER_SOFT": "#331a1c",
    "PRESSED": "#232838", "MUTED": "#232838", "TRACK": "#2a3040",
    "SEG_ACTIVE": "#353c52",
    "SCROLL": "#3a4152", "SCROLL_HOVER": "#4d566b", "PRIMARY_DISABLED": "#3b4170",
    "TOOLTIP_BG": "#e7e9f0", "TOOLTIP_FG": "#171b24",
    "SHADOW": "#000000",
}

MODE = "light"
globals().update(LIGHT)


def set_mode(mode):
    """Switch every colour constant in this module to the light or dark palette.

    Only changes the constants; call switch_theme() to also restyle a
    running application."""
    global MODE
    MODE = "dark" if mode == "dark" else "light"
    globals().update(DARK if MODE == "dark" else LIGHT)


def _settings():
    return QtCore.QSettings("Whisper", "Whisper")


def _system_prefers_dark():
    """Windows' "app mode" setting; False anywhere else or if unreadable."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def saved_mode():
    """The remembered theme; on first run, follow the Windows setting."""
    value = _settings().value("theme", "")
    if value in ("light", "dark"):
        return value
    return "dark" if _system_prefers_dark() else "light"


def save_mode(mode):
    _settings().setValue("theme", mode)


def color(token):
    """The current value of a palette token, e.g. color("ACCENT")."""
    return globals()[token]


def mix(a, b, t):
    """Linear blend of two colours (hex strings or QColor), t in 0..1."""
    a, b = QtGui.QColor(a), QtGui.QColor(b)
    t = max(0.0, min(1.0, t))
    return QtGui.QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t))


def alpha(c, a):
    """A colour with its alpha set to a (0..255)."""
    c = QtGui.QColor(c)
    c.setAlpha(int(a))
    return c


# --- theme change notifications -----------------------------------------

_listeners = []


def themed(fn, owner=None):
    """Call fn now, and again every time the theme changes.

    Use it for anything that bakes a palette colour into a widget at build
    time (an inline stylesheet, an icon pixmap). If owner is given, the
    callback is dropped when that QObject is destroyed."""
    entry = [fn]
    _listeners.append(entry)
    if owner is not None:
        owner.destroyed.connect(lambda *_: entry in _listeners and _listeners.remove(entry))
    fn()
    return fn


def _notify():
    for entry in list(_listeners):
        try:
            entry[0]()
        except RuntimeError:                 # the widget behind it is gone
            if entry in _listeners:
                _listeners.remove(entry)


def apply_titlebar(window):
    """Dark or light native title bar on Windows 10/11; no-op elsewhere."""
    if sys.platform != "win32" or window is None:
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        value = ctypes.c_int(1 if MODE == "dark" else 0)
        for attribute in (20, 19):           # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


def switch_theme(mode=None, animate=True):
    """Switch light <-> dark (or to `mode`) in a running app, keeping state.

    The old look is snapshotted and faded out over the new one, so the
    change feels like one smooth transition instead of a flash."""
    app = QtWidgets.QApplication.instance()
    mode = mode or ("light" if MODE == "dark" else "dark")
    windows = [w for w in app.topLevelWidgets() if w.isVisible() and w.isWindow()]
    snapshots = []
    if animate:
        for w in windows:
            if isinstance(w, QtWidgets.QMainWindow):
                snapshots.append((w, w.grab()))
    set_mode(mode)
    save_mode(mode)
    apply(app)
    _notify()
    app.setWindowIcon(app_icon())
    for w in windows:
        apply_titlebar(w)
    for w, pixmap in snapshots:
        _fade_out_snapshot(w, pixmap)


def _fade_out_snapshot(window, pixmap):
    cover = QtWidgets.QLabel(window)
    cover.setPixmap(pixmap)
    cover.setGeometry(window.rect())
    cover.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
    effect = QtWidgets.QGraphicsOpacityEffect(cover)
    cover.setGraphicsEffect(effect)
    cover.show()
    cover.raise_()
    anim = QtCore.QPropertyAnimation(effect, b"opacity", cover)
    anim.setDuration(280)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)
    anim.finished.connect(cover.deleteLater)
    anim.start()


# --- type -------------------------------------------------------------

SANS_STACK = '"Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", sans-serif'
SANS_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue"]
_FAMILY = None


def font(size=13, weight=QtGui.QFont.Normal):
    """A UI QFont for painted widgets, using the first family installed."""
    global _FAMILY
    f = QtGui.QFont()
    if _FAMILY is None:
        for family in SANS_FAMILIES:
            f.setFamily(family)
            if QtGui.QFontInfo(f).family().lower() == family.lower():
                _FAMILY = family
                break
        else:
            _FAMILY = f.family()
    f.setFamily(_FAMILY)
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
        background: %(tooltip_bg)s; color: %(tooltip_fg)s; border: none;
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
        background: %(accent_soft)s; color: %(accent_text)s;
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
    QFrame#vsep { background: %(border)s; }

    /* --- inputs: these take focus from a click, so they show it themselves --- */
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
    QLineEdit:hover, QPlainTextEdit:hover { border-color: %(border_hover)s; }
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
        border: 2px solid %(accent)s;
        padding: 8px 11px;
    }
    QPlainTextEdit[readOnly="true"] { background: %(surface_alt)s; }
    QPlainTextEdit[readOnly="true"]:focus { border: 1px solid %(border_strong)s; padding: 9px 12px; }

    QComboBox {
        background: %(surface)s;
        border: 1px solid %(border_strong)s;
        border-radius: 10px;
        padding: 8px 12px;
        min-height: 22px;
        font-size: 14px;
    }
    QComboBox:hover { border-color: %(border_hover)s; }
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

    /* --- buttons (keyboard focus is drawn by the focus ring, not here) --- */
    QAbstractButton, QComboBox { outline: none; }
    QPushButton {
        background: %(surface)s;
        color: %(text)s;
        border: 1px solid %(border_strong)s;
        border-radius: 10px;
        padding: 9px 16px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover { background: %(surface_alt)s; border-color: %(border_hover)s; }
    QPushButton:pressed { background: %(pressed)s; }
    QPushButton:checked { background: %(muted)s; border-color: %(border_hover)s; }
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
    QPushButton#primary:disabled { background: %(primary_disabled)s; color: rgba(255,255,255,0.85); }

    QPushButton#ghost {
        background: transparent;
        border: none;
        color: %(text_dim)s;
        padding: 8px 12px;
        font-weight: 500;
    }
    QPushButton#ghost:hover { background: %(muted)s; color: %(text)s; }
    QPushButton#ghost:pressed { background: %(pressed)s; }

    QPushButton#link {
        background: transparent;
        border: none;
        color: %(accent_text)s;
        padding: 6px 8px;
        font-weight: 600;
    }
    QPushButton#link:hover { color: %(accent_hover)s; text-decoration: underline; }

    /* --- segmented switch: the white pill is painted and slides --- */
    QFrame#segment {
        background: %(muted)s;
        border-radius: 11px;
    }
    QPushButton#segBtn, QPushButton#segBtn:checked, QPushButton#segBtn:hover,
    QPushButton#segBtn:pressed {
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
    }
    QPushButton#segBtn { color: %(text_dim)s; }
    QPushButton#segBtn:hover, QPushButton#segBtn:checked { color: %(text)s; }
    QPushButton#segBtn:disabled { color: %(text_faint)s; }

    /* --- scrollbars --- */
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
    QScrollBar::handle:vertical { background: %(scroll)s; border-radius: 3px; min-height: 30px; }
    QScrollBar::handle:vertical:hover { background: %(scroll_hover)s; }
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
        "accent_text": ACCENT_TEXT,
        "success": SUCCESS, "success_soft": SUCCESS_SOFT,
        "border_hover": BORDER_HOVER, "pressed": PRESSED, "muted": MUTED,
        "scroll": SCROLL, "scroll_hover": SCROLL_HOVER,
        "primary_disabled": PRIMARY_DISABLED,
        "tooltip_bg": TOOLTIP_BG, "tooltip_fg": TOOLTIP_FG,
        "sans": SANS_STACK,
        "chevron": _chevron_path(),
    }


def _chevron_path():
    """Writes a small chevron PNG for the combo box arrow; QSS needs a file."""
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "whisper_chevron_%s.png" % MODE)
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
    """Applies the palette and stylesheet to a QApplication.

    Safe to call again after set_mode(): it re-polishes every widget."""
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
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(TOOLTIP_BG))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(TOOLTIP_FG))
    palette.setColor(QtGui.QPalette.Link, QtGui.QColor(ACCENT_TEXT))
    app.setPalette(palette)
    app.setFont(font(14))
    app.setStyleSheet(stylesheet())
    _Interaction.install(app)


def app_icon():
    """The window/taskbar icon: a white padlock on an accent tile."""
    icon_ = QtGui.QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(ACCENT))
        p.drawRoundedRect(QtCore.QRectF(0, 0, size, size), size * 0.24, size * 0.24)
        inner = int(size * 0.56)
        p.drawPixmap((size - inner) // 2, (size - inner) // 2,
                     icon_pixmap("lock", inner, "#ffffff", dpr=1.0))
        p.end()
        icon_.addPixmap(pm)
    return icon_


# --- interaction: hover cursor, click-vs-keyboard focus, focus ring ------

_TEXT_INPUTS = (QtWidgets.QLineEdit, QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit,
                QtWidgets.QAbstractSpinBox)
_KEYBOARD_REASONS = (QtCore.Qt.TabFocusReason, QtCore.Qt.BacktabFocusReason,
                     QtCore.Qt.ShortcutFocusReason)


class _Interaction(QtCore.QObject):
    """App-wide event filter implementing the interaction model above."""

    _instance = None

    @classmethod
    def install(cls, app):
        if cls._instance is None:
            cls._instance = cls(app)
            app.installEventFilter(cls._instance)
            # Widgets created before install() never get a Polish event here.
            for w in app.allWidgets():
                cls._instance._adopt(w)

    def __init__(self, parent):
        super(_Interaction, self).__init__(parent)
        self._keyboard = False
        self._ring_target = None

    def _adopt(self, w):
        if isinstance(w, (QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
            w.setTabChangesFocus(True)        # Tab moves on instead of typing a tab
        elif isinstance(w, (QtWidgets.QAbstractButton, QtWidgets.QComboBox)):
            if w.focusPolicy() != QtCore.Qt.NoFocus:
                w.setFocusPolicy(QtCore.Qt.TabFocus)
            if isinstance(w, QtWidgets.QAbstractButton):
                w.setCursor(QtCore.Qt.PointingHandCursor)
        elif (isinstance(w, QtWidgets.QAbstractScrollArea)
              and not isinstance(w, _TEXT_INPUTS + (QtWidgets.QAbstractItemView,))):
            w.setFocusPolicy(QtCore.Qt.NoFocus)

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QtCore.QEvent.Polish and isinstance(obj, QtWidgets.QWidget):
            self._adopt(obj)
        elif t in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonDblClick):
            if self._keyboard:
                self._keyboard = False
                FocusRing.hide_all()
        elif t == QtCore.QEvent.KeyPress and event.key() in (
                QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
            self._keyboard = True
        elif t == QtCore.QEvent.FocusIn and isinstance(obj, QtWidgets.QWidget):
            keyboard = event.reason() in _KEYBOARD_REASONS or (
                self._keyboard and event.reason() == QtCore.Qt.OtherFocusReason)
            if keyboard and obj.isWindow() is False and not isinstance(obj, _TEXT_INPUTS):
                FocusRing.show_for(obj)
            else:
                FocusRing.hide_all()
        elif t == QtCore.QEvent.FocusOut and isinstance(obj, QtWidgets.QWidget):
            FocusRing.hide_for(obj)
        return False


class FocusRing(QtWidgets.QWidget):
    """A keyboard-focus halo drawn on an overlay above the whole window.

    Drawn outside the widget with a 3 px gap so it never shifts the layout
    and works the same for every kind of control. A widget can supply
    focus_ring_rect() (in its own coordinates) and focus_ring_radius()."""

    GAP = 3

    def __init__(self, window):
        super(FocusRing, self).__init__(window)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._target = None
        self._watched = []
        self._opacity = 0.0
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._set_opacity)
        self.hide()

    # -- class helpers -------------------------------------------------

    @staticmethod
    def _for_window(widget):
        window = widget.window()
        ring = window.findChild(FocusRing, "", QtCore.Qt.FindDirectChildrenOnly)
        if ring is None:
            ring = FocusRing(window)
        return ring

    @classmethod
    def show_for(cls, widget):
        cls._for_window(widget).attach(widget)

    @classmethod
    def hide_for(cls, widget):
        window = widget.window()
        ring = window.findChild(FocusRing, "", QtCore.Qt.FindDirectChildrenOnly)
        if ring is not None and ring._target is widget:
            ring.detach()

    @classmethod
    def hide_all(cls):
        app = QtWidgets.QApplication.instance()
        for w in app.topLevelWidgets():
            for ring in w.findChildren(FocusRing, "", QtCore.Qt.FindDirectChildrenOnly):
                ring.detach()

    # -- tracking ------------------------------------------------------

    def attach(self, widget):
        self._unwatch()
        self._target = widget
        w = widget
        while w is not None and w is not self.parentWidget():
            w.installEventFilter(self)
            self._watched.append(w)
            w = w.parentWidget()
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.update()

    def detach(self):
        self._unwatch()
        self._target = None
        self._opacity = 0.0
        self.hide()

    def _unwatch(self):
        for w in self._watched:
            try:
                w.removeEventFilter(self)
            except RuntimeError:
                pass
        self._watched = []

    def _set_opacity(self, value):
        self._opacity = float(value)
        self.update()

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Move, QtCore.QEvent.Resize,
                            QtCore.QEvent.Show, QtCore.QEvent.Hide):
            if obj is self.parentWidget():
                self.setGeometry(obj.rect())
            self.update()
            if event.type() == QtCore.QEvent.Hide and obj is self._target:
                self.detach()
        return False

    def paintEvent(self, event):
        target = self._target
        if target is None or not target.isVisible():
            return
        try:
            local = (target.focus_ring_rect() if hasattr(target, "focus_ring_rect")
                     else QtCore.QRectF(target.rect()))
            radius = (target.focus_ring_radius() if hasattr(target, "focus_ring_radius")
                      else _corner_radius(target))
        except RuntimeError:
            return
        top_left = target.mapTo(self.parentWidget(), QtCore.QPoint(0, 0))
        rect = QtCore.QRectF(local).translated(top_left.x(), top_left.y())
        g = self.GAP
        rect = rect.adjusted(-g, -g, g, g)

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        clip = self._clip_rect(target)
        if clip is not None:
            p.setClipRect(clip)
        a = self._opacity
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(alpha(ACCENT, 70 * a), 6))           # soft outer halo
        p.drawRoundedRect(rect, radius + g, radius + g)
        p.setPen(QtGui.QPen(alpha(ACCENT_TEXT if MODE == "dark" else ACCENT, 255 * a), 2))
        p.drawRoundedRect(rect, radius + g, radius + g)

    def _clip_rect(self, target):
        """Keep the ring inside the scroll viewport the target lives in."""
        w = target.parentWidget()
        while w is not None and w is not self.parentWidget():
            if isinstance(w, QtWidgets.QAbstractScrollArea):
                vp = w.viewport()
                origin = vp.mapTo(self.parentWidget(), QtCore.QPoint(0, 0))
                return QtCore.QRectF(origin.x() - 6, origin.y(), vp.width() + 12, vp.height())
            w = w.parentWidget()
        return None


def _corner_radius(widget):
    name = widget.objectName()
    if name == "segBtn":
        return 8
    if name in ("primary", "ghost", "link"):
        return 10
    return 10


# --- animation helper -------------------------------------------------


class Tween(QtCore.QObject):
    """A float that glides toward a target and repaints its owner."""

    def __init__(self, owner, duration=170, curve=QtCore.QEasingCurve.OutCubic):
        super(Tween, self).__init__(owner)
        self.value = 0.0
        self._owner = owner
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(curve)
        self._anim.valueChanged.connect(self._step)

    def _step(self, v):
        self.value = float(v)
        self._owner.update()

    def to(self, target):
        if abs(self.value - target) < 1e-3 and self._anim.state() != QtCore.QAbstractAnimation.Running:
            return
        self._anim.stop()
        self._anim.setStartValue(self.value)
        self._anim.setEndValue(float(target))
        self._anim.start()


def paint_shadow(p, rect, radius, strength, color=None):
    """A soft drop shadow under rect: a few stacked translucent rounded rects."""
    if strength <= 0.01:
        return
    color = color or SHADOW
    base = 34 if MODE == "light" else 90
    p.save()
    p.setPen(QtCore.Qt.NoPen)
    steps = 7
    for i in range(steps, 0, -1):
        spread = i * 1.6
        a = base * strength * (1 - i / (steps + 1)) / steps * 2.2
        p.setBrush(alpha(color, a))
        p.drawRoundedRect(rect.adjusted(-spread, -spread + 2 * strength + 1,
                                        spread, spread + 4 * strength + 1),
                          radius + spread, radius + spread)
    p.restore()


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
    elif name == "sun":
        import math
        p.drawEllipse(pt(0.5, 0.5), s * 0.17, s * 0.17)
        for k in range(8):
            ang = k * math.pi / 4
            c, d = math.cos(ang), math.sin(ang)
            p.drawLine(pt(0.5 + 0.29 * c, 0.5 + 0.29 * d), pt(0.5 + 0.40 * c, 0.5 + 0.40 * d))
    elif name == "moon":
        outer = QtGui.QPainterPath()
        outer.addEllipse(pt(0.48, 0.52), s * 0.32, s * 0.32)
        bite = QtGui.QPainterPath()
        bite.addEllipse(pt(0.66, 0.36), s * 0.26, s * 0.26)
        p.drawPath(outer.subtracted(bite))
    elif name == "copy":
        p.drawRoundedRect(QtCore.QRectF(pt(0.34, 0.34), pt(0.84, 0.84)), s * 0.08, s * 0.08)
        p.drawPolyline(QtGui.QPolygonF([pt(0.66, 0.22), pt(0.66, 0.16), pt(0.16, 0.16),
                                        pt(0.16, 0.66), pt(0.22, 0.66)]))
    elif name == "save":
        p.drawLine(pt(0.5, 0.16), pt(0.5, 0.60))
        p.drawPolyline(QtGui.QPolygonF([pt(0.32, 0.43), pt(0.5, 0.61), pt(0.68, 0.43)]))
        p.drawPolyline(QtGui.QPolygonF([pt(0.18, 0.64), pt(0.18, 0.84), pt(0.82, 0.84), pt(0.82, 0.64)]))
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


def _dpr():
    app = QtWidgets.QApplication.instance()
    return app.devicePixelRatio() if app else 1.0


def icon_pixmap(name, size=20, color=None, width=None, gap=0, dpr=None):
    """A crisp, DPI-aware pixmap of a line icon.

    gap adds transparent space on the right, which is how buttons get a
    comfortable distance between their icon and their text."""
    color = color or TEXT
    dpr = dpr or _dpr()
    pm = QtGui.QPixmap(int((size + gap) * dpr), int(size * dpr))
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


def icon(name, size=18, color=None, gap=0):
    return QtGui.QIcon(icon_pixmap(name, size, color, gap=gap))


def set_button_icon(button, name, color="TEXT_DIM", size=16, gap=7):
    """Give a button a line icon with proper spacing before its text.

    color is a palette token name (re-tinted when the theme changes) or a
    fixed colour such as "#ffffff"."""
    def refresh():
        c = color if color.startswith("#") else globals()[color]
        button.setIcon(icon(name, size, c, gap=gap if button.text() else 0))
        button.setIconSize(QtCore.QSize(size + (gap if button.text() else 0), size))
    themed(refresh, button)


def icon_label(name, size=20, color=None):
    """A QLabel showing an icon; color may be a palette token name."""
    label_ = QtWidgets.QLabel()
    label_.setFixedSize(size, size)
    if color and not color.startswith("#") and color in LIGHT:
        themed(lambda: label_.setPixmap(icon_pixmap(name, size, globals()[color])), label_)
    else:
        label_.setPixmap(icon_pixmap(name, size, color))
    return label_


# --- reusable widgets -------------------------------------------------


def label(text, name=None, wrap=False):
    w = QtWidgets.QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


class ElidedLabel(QtWidgets.QLabel):
    """A one-line label that shortens long text with an ellipsis."""

    def __init__(self, text="", parent=None):
        super(ElidedLabel, self).__init__(parent)
        self._full = ""
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.setText(text)

    def setText(self, text):
        self._full = text
        self.setToolTip(text if text else "")
        self._elide()

    def full_text(self):
        return self._full

    def resizeEvent(self, event):
        super(ElidedLabel, self).resizeEvent(event)
        self._elide()

    def _elide(self):
        metrics = QtGui.QFontMetrics(self.font())
        shown = metrics.elidedText(self._full, QtCore.Qt.ElideMiddle, max(10, self.width()))
        QtWidgets.QLabel.setText(self, shown)


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
        self._done = False

    def set_done(self, done):
        """Turns the number into a green check once the step is complete."""
        if done == self._done:
            return
        self._done = done
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
        self._hover = Tween(self, 180)
        self._drag = Tween(self, 140)
        self._press = Tween(self, 90)
        self.setAcceptDrops(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.TabFocus)   # a click opens the dialog, it doesn't focus
        self.setMinimumHeight(height)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setAccessibleName("%s. %s" % (title, subtitle))

    def focus_ring_radius(self):
        return 12

    def sizeHint(self):
        return QtCore.QSize(400, self.minimumHeight())

    def open_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window(), self.dialog_title, "", self.file_filter)
        if path:
            self.fileChosen.emit(path)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press.to(1.0)

    def mouseReleaseEvent(self, event):
        self._press.to(0.0)
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.open_dialog()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space):
            self.open_dialog()
        else:
            super(DropZone, self).keyPressEvent(event)

    def enterEvent(self, event):
        self._hover.to(1.0)

    def leaveEvent(self, event):
        self._hover.to(0.0)
        self._press.to(0.0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag.to(1.0)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drag.to(0.0)

    def dropEvent(self, event):
        self._drag.to(0.0)
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile():
            self.fileChosen.emit(urls[0].toLocalFile())

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        h = max(self._hover.value, self._drag.value)
        d = self._drag.value
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = mix(SURFACE_ALT, ACCENT_SOFT, h)
        if self._press.value:
            bg = mix(bg, ACCENT_SOFT_BORDER, 0.35 * self._press.value)
        p.setBrush(bg)
        pen = QtGui.QPen(mix(BORDER_STRONG, ACCENT, h), 1.5 + 0.5 * d)
        if d < 0.5:
            pen.setStyle(QtCore.Qt.CustomDashLine)
            pen.setDashPattern([5, 4])
        p.setPen(pen)
        p.drawRoundedRect(rect, 12, 12)

        cy = self.height() / 2.0
        lift = 3 * h
        cx = self.width() / 2.0
        # icon bubble: surface tile that turns accent while you hover/drag
        p.setPen(QtCore.Qt.NoPen)
        paint_shadow(p, QtCore.QRectF(cx - 22, cy - 48 - lift, 44, 44), 22, 0.5 * h)
        p.setBrush(mix(SURFACE, ACCENT, h))
        p.drawEllipse(QtCore.QPointF(cx, cy - 26 - lift), 22, 22)
        pm = icon_pixmap(self.icon_name, 22, mix(ACCENT_TEXT, QtGui.QColor("#ffffff"), h).name())
        p.drawPixmap(int(cx - 11), int(cy - 37 - lift), pm)

        p.setPen(QtGui.QColor(TEXT))
        p.setFont(font(14, QtGui.QFont.DemiBold))
        title = "Drop it to use this file" if d > 0.5 else self.title
        p.drawText(QtCore.QRectF(0, cy + 4, self.width(), 22), QtCore.Qt.AlignCenter, title)
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
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self._file_args = None
        self._badge_args = ("", "neutral")
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
        self.name = ElidedLabel()
        self.name.setObjectName("fileName")
        self.details = ElidedLabel()
        self.details.setObjectName("hint")
        self.badge = QtWidgets.QLabel()
        self.badge.hide()
        text.addStretch()
        text.addWidget(self.name)
        text.addWidget(self.details)
        text.addWidget(self.badge, 0, QtCore.Qt.AlignLeft)
        text.addStretch()
        row.addLayout(text, 1)

        self.change_btn = QtWidgets.QPushButton("Change")
        self.change_btn.clicked.connect(self.changeRequested)
        row.addWidget(self.change_btn)
        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.remove_btn.setObjectName("ghost")
        self.remove_btn.clicked.connect(self.removeRequested)
        row.addWidget(self.remove_btn)
        themed(self._restyle, self)

    def _restyle(self):
        if self._file_args is not None:
            self._paint_thumb(*self._file_args[2:])
        self.set_badge(*self._badge_args)

    def set_file(self, name, details, thumb_path=None, icon_name="file"):
        self._file_args = (name, details, thumb_path, icon_name)
        self.name.setText(name)
        self.details.setText(details)
        self._paint_thumb(thumb_path, icon_name)

    def _paint_thumb(self, thumb_path, icon_name):
        pm = None
        if thumb_path:
            pm = QtGui.QPixmap(thumb_path)
            if pm.isNull():
                pm = None
        if pm is None:
            self.thumb.setPixmap(icon_pixmap(icon_name, 26, ACCENT_TEXT))
            return
        dpr = _dpr()
        side = int(56 * dpr)
        pm = pm.scaled(side, side, QtCore.Qt.KeepAspectRatioByExpanding,
                       QtCore.Qt.SmoothTransformation)
        out = QtGui.QPixmap(side, side)
        out.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(out)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(QtCore.QRectF(0, 0, side, side), 8 * dpr, 8 * dpr)
        painter.setClipPath(clip)
        painter.drawPixmap(int((side - pm.width()) / 2), int((side - pm.height()) / 2), pm)
        painter.end()
        out.setDevicePixelRatio(dpr)
        self.thumb.setPixmap(out)

    def set_badge(self, text, kind="neutral"):
        self._badge_args = (text, kind)
        if not text:
            self.badge.hide()
            return
        fg, bg = {
            "success": (SUCCESS, SUCCESS_SOFT),
            "warn": (WARN, WARN_SOFT),
            "danger": (DANGER, DANGER_SOFT),
        }.get(kind, (TEXT_DIM, MUTED))
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
        self.card.removeRequested.connect(self._remove)
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

    def _remove(self):
        keyboard = self.card.remove_btn.hasFocus()
        self.set_path("")
        if keyboard:                        # keep keyboard users where they were
            self.zone.setFocus(QtCore.Qt.TabFocusReason)

    def set_path(self, path):
        self.path = os.path.abspath(path) if path else ""
        self.zone.setVisible(not self.path)
        self.card.setVisible(bool(self.path))
        self.fileChanged.emit(self.path)


class Segmented(QtWidgets.QFrame):
    """A pill-shaped switch between a few options; the pill slides."""

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
        self._icons = []
        for index, (text, icon_name) in enumerate(options):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            self.group.addButton(btn, index)
            row.addWidget(btn)
            self.buttons.append(btn)
            self._icons.append(icon_name)
            btn.installEventFilter(self)
        self.buttons[0].setChecked(True)
        self._pill = None                       # QRectF, animated
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._set_pill)
        self.group.buttonToggled.connect(self._on_toggled)
        self.group.buttonClicked.connect(lambda b: self.changed.emit(self.group.id(b)))
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        themed(self._refresh_icons, self)

    def _refresh_icons(self):
        for btn, name in zip(self.buttons, self._icons):
            if not name:
                continue
            c = TEXT if btn.isChecked() else TEXT_DIM
            if not btn.isEnabled():
                c = TEXT_FAINT
            btn.setIcon(icon(name, 16, c, gap=7))
            btn.setIconSize(QtCore.QSize(23, 16))
        self.update()

    def _target_rect(self):
        btn = self.group.checkedButton()
        return QtCore.QRectF(btn.geometry()) if btn is not None else None

    def _on_toggled(self, button, checked):
        self._refresh_icons()
        if not checked:
            return
        target = self._target_rect()
        if self._pill is None or not self.isVisible():
            self._pill = target
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._pill)
        self._anim.setEndValue(target)
        self._anim.start()

    def _set_pill(self, rect):
        self._pill = QtCore.QRectF(rect)
        self.update()

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Move, QtCore.QEvent.Resize) and obj.isChecked():
            if self._anim.state() != QtCore.QAbstractAnimation.Running:
                self._pill = self._target_rect()
                self.update()
        elif event.type() == QtCore.QEvent.EnabledChange:
            self._refresh_icons()
        return False

    def paintEvent(self, event):
        super(Segmented, self).paintEvent(event)
        if self._pill is None:
            self._pill = self._target_rect()
        if self._pill is None:
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        paint_shadow(p, self._pill, 8, 0.35)
        p.setPen(QtGui.QPen(QtGui.QColor(BORDER), 1))
        p.setBrush(QtGui.QColor(SEG_ACTIVE))
        p.drawRoundedRect(self._pill.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

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
        self._shown = 0.0
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._step)
        self.setFixedHeight(8)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)

    def _step(self, v):
        self._shown = float(v)
        self.update()

    def set_unknown(self):
        self._known = False
        self._ratio = 0.0
        self._shown = 0.0
        self.update()

    def set_ratio(self, ratio):
        self._known = True
        self._ratio = max(0.0, float(ratio))
        self._anim.stop()
        self._anim.setStartValue(self._shown)
        self._anim.setEndValue(min(self._ratio, 1.0))
        self._anim.start()

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
        p.setBrush(QtGui.QColor(TRACK))
        p.drawRoundedRect(QtCore.QRectF(self.rect()), r, r)
        if self._known and self._ratio > 0:
            w = max(self.height(), self.width() * self._shown)
            p.setBrush(QtGui.QColor(self.colour()))
            p.drawRoundedRect(QtCore.QRectF(0, 0, w, self.height()), r, r)


class StrengthMeter(QtWidgets.QWidget):
    """Four short segments and a word: how hard a password is to guess."""

    def __init__(self, parent=None):
        super(StrengthMeter, self).__init__(parent)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.segments = []
        for _ in range(4):
            seg = QtWidgets.QFrame()
            seg.setFixedHeight(5)
            row.addWidget(seg, 1)
            self.segments.append(seg)
        row.addSpacing(8)
        self.word = QtWidgets.QLabel("")
        self.word.setObjectName("hint")
        self.word.setMinimumWidth(80)
        row.addWidget(self.word)
        self._score = (0, "")
        themed(lambda: self.set_score(*self._score), self)

    def set_score(self, score, word):
        self._score = (score, word)
        colour = (DANGER, DANGER, WARN, SUCCESS, SUCCESS)[max(0, min(4, score))]
        lit = 0 if not word else max(1, score)
        for i, seg in enumerate(self.segments):
            seg.setStyleSheet("background: %s; border-radius: 2px;"
                              % (colour if i < lit else TRACK))
        self.word.setText(word)
        self.word.setStyleSheet("color: %s; font-weight: 600;" % colour if word else "")


class Spinner(QtWidgets.QWidget):
    """A small rotating arc for 'working on it'."""

    def __init__(self, size=18, parent=None):
        super(Spinner, self).__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def showEvent(self, event):
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QtGui.QPen(alpha(ACCENT_TEXT, 50), 2.2))
        p.drawEllipse(r)
        pen = QtGui.QPen(QtGui.QColor(ACCENT_TEXT), 2.2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(-self._angle * 16), int(100 * 16))


class Banner(QtWidgets.QFrame):
    """A soft coloured message strip with an icon and optional action."""

    @staticmethod
    def _kinds():
        return {
            "info": ("info", ACCENT_TEXT, ACCENT_SOFT),
            "success": ("check", SUCCESS, SUCCESS_SOFT),
            "warn": ("alert", WARN, WARN_SOFT),
            "error": ("alert", DANGER, DANGER_SOFT),
            "busy": (None, ACCENT_TEXT, ACCENT_SOFT),
        }

    def __init__(self, parent=None):
        super(Banner, self).__init__(parent)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(12, 9, 10, 9)
        row.setSpacing(10)
        self.icon = QtWidgets.QLabel()
        self.icon.setFixedSize(18, 18)
        row.addWidget(self.icon, 0, QtCore.Qt.AlignTop)
        self.spinner = Spinner(18)
        self.spinner.hide()
        row.addWidget(self.spinner, 0, QtCore.Qt.AlignTop)
        self.text = QtWidgets.QLabel()
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        row.addWidget(self.text, 1)
        self.action = QtWidgets.QPushButton()
        self.action.setObjectName("link")
        self.action.hide()
        row.addWidget(self.action, 0, QtCore.Qt.AlignVCenter)
        self._action_cb = None
        self._last = None
        self.action.clicked.connect(self._run_action)
        self.hide()
        themed(self._restyle, self)

    def _run_action(self):
        if self._action_cb:
            self._action_cb()

    def _restyle(self):
        if self._last is not None and self.isVisible():
            self.show_message(*self._last)

    def show_message(self, kind, text, action_text=None, action=None):
        self._last = (kind, text, action_text, action)
        kinds = self._kinds()
        icon_name, fg, bg = kinds.get(kind, kinds["info"])
        self.setStyleSheet(
            "Banner { background: %s; border-radius: 10px; }"
            "QLabel { color: %s; font-size: 13px; }" % (bg, TEXT))
        if icon_name is None:
            self.icon.hide()
            self.spinner.show()
        else:
            self.spinner.hide()
            self.icon.setPixmap(icon_pixmap(icon_name, 18, fg))
            self.icon.show()
        self.text.setText(text)
        self._action_cb = action
        if action_text and action:
            self.action.setText(action_text)
            self.action.show()
        else:
            self.action.hide()
        self.show()

    def clear(self):
        self._last = None
        self.hide()


class ThemeButton(QtWidgets.QPushButton):
    """Ghost button that flips between the light and dark theme."""

    def __init__(self, parent=None):
        super(ThemeButton, self).__init__(parent)
        self.setObjectName("ghost")
        self.setToolTip("Switch between the light and dark theme (Ctrl+Shift+L)")
        self.clicked.connect(lambda: switch_theme())
        themed(self._refresh, self)

    def _refresh(self):
        dark = MODE == "dark"
        self.setText("Light theme" if dark else "Dark theme")
        self.setIcon(icon("sun" if dark else "moon", 16, TEXT_DIM, gap=7))
        self.setIconSize(QtCore.QSize(23, 16))


# --- page scaffolding -------------------------------------------------


class Page(QtWidgets.QWidget):
    """A page with a top bar (back + title), a scrolling centred column,
    and a fixed action bar at the bottom.

    Keyboard: Esc or Alt+Left goes back, Ctrl+Enter runs the primary
    action (set self.primary_btn)."""

    def __init__(self, title, on_back=None, parent=None):
        super(Page, self).__init__(parent)
        self.setObjectName("page")
        self.primary_btn = None
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QtWidgets.QFrame()
        top.setObjectName("topBar")
        top_row = QtWidgets.QHBoxLayout(top)
        top_row.setContentsMargins(16, 10, 16, 10)
        top_row.setSpacing(8)
        self.back_btn = QtWidgets.QPushButton("Home")
        self.back_btn.setObjectName("ghost")
        self.back_btn.setToolTip("Back to the start screen (Esc)")
        set_button_icon(self.back_btn, "back")
        if on_back:
            self.back_btn.clicked.connect(on_back)
        else:
            self.back_btn.hide()
        top_row.addWidget(self.back_btn)
        # Parent it before touching visibility: setVisible(True) on a widget
        # with no parent briefly makes it a window of its own, which steals
        # activation (and keyboard focus) from the main window.
        sep = QtWidgets.QFrame(top)
        sep.setObjectName("vsep")
        sep.setFixedSize(1, 20)
        top_row.addWidget(sep)
        sep.setVisible(bool(on_back))
        top_row.addSpacing(6)
        top_row.addWidget(label(title, "pageTitle"))
        top_row.addStretch()
        self.theme_btn = ThemeButton()
        top_row.addWidget(self.theme_btn)
        outer.addWidget(top)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setFocusPolicy(QtCore.Qt.NoFocus)
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

        ctx = QtCore.Qt.WidgetWithChildrenShortcut
        if on_back:
            for seq in ("Esc", "Alt+Left"):
                sc = QtWidgets.QShortcut(QtGui.QKeySequence(seq), self, on_back)
                sc.setContext(ctx)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(seq), self, self._run_primary)
            sc.setContext(ctx)

    def _run_primary(self):
        if self.primary_btn is not None and self.primary_btn.isEnabled():
            self.primary_btn.click()

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
        self.toggle.setToolTip("Show or hide the password")
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
