"""The Hide page: put a message or picture inside a PNG or MP3.

Three plain steps -- choose a file, write what to hide, set a password --
and one button that saves a copy with the secret inside. All engine calls
are unchanged from the previous version; only the presentation is new.

The engine work runs on a QThread so the window never freezes, and a
second click while one is running is ignored.
"""

import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import gui  # sets sys.path for both the GUI and the engine

from gui import capacity, theme
# Flat imports so the engine doesn't get loaded twice (see gui/__init__.py).
from protection import PasswordProtection
from StegoTextPass import StegoTextPass
from steganography import TextSteganography

MODE_TEXT = "text"
MODE_IMAGE = "image"

IMAGE_CARRIERS = (".png",)
AUDIO_CARRIERS = (".mp3",)

# (label shown to the user, engine value, explanation)
PROTECTION = [
    ("Strong — AES-256 encryption (recommended)", "Strong",
     "Without the password the message can't be read. Use a long password: "
     "anyone who has the file can keep guessing offline."),
    ("Basic — scrambled, not encrypted", "Medium",
     "Hides the text from a casual look, but it is not real encryption."),
    ("Minimal — simple letter shift", "Weak",
     "Easy to undo for anyone who tries. Only for fun."),
]


class EmbedWorker(QtCore.QThread):
    """Runs one embed operation off the UI thread."""

    finished_ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, kind, args, parent=None):
        super(EmbedWorker, self).__init__(parent)
        self.kind = kind
        self.args = args

    def run(self):
        try:
            stego = StegoTextPass()
            if self.kind == MODE_TEXT:
                carrier, message, password, algo, output = self.args
                stego.encode_text_with_password(carrier, message, password,
                                                algo, output)
            else:
                carrier, secret, password, algo, output = self.args
                stego.encode_image_with_password(carrier, secret, password,
                                                 algo, output)
            self.finished_ok.emit(self.args[-1])
        except Exception as exc:
            self.failed.emit(str(exc))


class HidePage(theme.Page):

    def __init__(self, on_back=None, parent=None):
        super(HidePage, self).__init__("Hide a message", on_back, parent)
        self._worker = None
        self._ready = False
        self._carrier_kind = None
        self._carrier_size = (0, 0)
        self._last_output = ""

        self.column.addWidget(self._carrier_step())
        self.column.addWidget(self._secret_step())
        self.column.addWidget(self._password_step())
        self.column.addStretch()

        self.banner = theme.Banner()
        self.actions.addWidget(self.banner, 1)
        self.actions.addStretch(0)
        self.embed_btn = QtWidgets.QPushButton("Hide and save…")
        self.embed_btn.setObjectName("primary")
        self.embed_btn.setIcon(theme.icon("lock", 16, "#ffffff"))
        self.embed_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.embed_btn.clicked.connect(self._start_embed)
        self.actions.addWidget(self.embed_btn, 0, QtCore.Qt.AlignRight)

        self._ready = True
        self._sync_mode()

    # -- step 1 --------------------------------------------------------

    def _carrier_step(self):
        self.step1 = theme.StepCard(
            1, "Choose a picture or song",
            "The secret goes inside this file. It will still look and sound "
            "the same.")
        self.carrier = theme.FilePicker(
            "Drop a PNG picture or MP3 song here", "or click to browse",
            "Choose a picture or song",
            "Pictures and songs (*.png *.mp3);;PNG picture (*.png);;"
            "MP3 song (*.mp3);;All files (*)")
        self.carrier.fileChanged.connect(self._on_carrier_changed)
        self.step1.body.addWidget(self.carrier)
        return self.step1

    # -- step 2 --------------------------------------------------------

    def _secret_step(self):
        self.step2 = theme.StepCard(2, "What do you want to hide?")

        top = QtWidgets.QHBoxLayout()
        self.mode = theme.Segmented([("Text message", "text"),
                                     ("Picture", "image")])
        self.mode.changed.connect(self._sync_mode)
        top.addWidget(self.mode)
        top.addStretch()
        self.load_text_btn = QtWidgets.QPushButton("Load from .txt file")
        self.load_text_btn.setObjectName("link")
        self.load_text_btn.clicked.connect(self._load_text_file)
        top.addWidget(self.load_text_btn)
        self.step2.body.addLayout(top)

        self.payload_edit = QtWidgets.QPlainTextEdit()
        self.payload_edit.setPlaceholderText("Type your secret message here…")
        self.payload_edit.setMinimumHeight(120)
        self.payload_edit.setMaximumHeight(180)
        self.payload_edit.textChanged.connect(self._refresh_budget)
        self.step2.body.addWidget(self.payload_edit)

        self.secret = theme.FilePicker(
            "Drop the picture to hide", "PNG only · or click to browse",
            "Choose the picture to hide", "PNG picture (*.png);;All files (*)",
            icon_name="image", height=120)
        self.secret.fileChanged.connect(self._on_secret_changed)
        self.step2.body.addWidget(self.secret)

        # space usage
        self.usage_box = QtWidgets.QWidget()
        usage = QtWidgets.QVBoxLayout(self.usage_box)
        usage.setContentsMargins(0, 4, 0, 0)
        usage.setSpacing(6)
        usage_head = QtWidgets.QHBoxLayout()
        usage_head.addWidget(theme.label("Space used in your file", "fieldLabel"))
        usage_head.addStretch()
        self.usage_value = theme.label("", "hint")
        usage_head.addWidget(self.usage_value)
        usage.addLayout(usage_head)
        self.meter = theme.UsageBar()
        usage.addWidget(self.meter)
        self.usage_note = theme.label("", "hint", wrap=True)
        usage.addWidget(self.usage_note)
        self.step2.body.addWidget(self.usage_box)
        return self.step2

    # -- step 3 --------------------------------------------------------

    def _password_step(self):
        self.step3 = theme.StepCard(
            3, "Lock it with a password",
            "You'll need this exact password to read the message later. "
            "It can't be recovered if you forget it.")

        self.key = theme.PasswordField("Choose a password")
        self.key.edit.textChanged.connect(self._update_steps)
        suggest = QtWidgets.QPushButton("Generate")
        suggest.setToolTip("Create a strong random password")
        suggest.clicked.connect(self._suggest_key)
        self.key.row.addWidget(suggest)
        self.step3.body.addLayout(theme.field("Password", self.key))

        self.cipher_combo = QtWidgets.QComboBox()
        for text, value, _ in PROTECTION:
            self.cipher_combo.addItem(text, value)
        self.cipher_combo.currentIndexChanged.connect(self._on_cipher_changed)
        self.protection_note = theme.label("", "hint", wrap=True)
        self.step3.body.addLayout(theme.field(
            "Protection", self.cipher_combo, self.protection_note))
        self._describe_cipher()
        return self.step3

    # -- helpers -------------------------------------------------------

    def _mode(self):
        return MODE_TEXT if self.mode.index() == 0 else MODE_IMAGE

    def _cipher(self):
        return self.cipher_combo.itemData(self.cipher_combo.currentIndex())

    def _sync_mode(self, *_):
        if not self._ready:
            return
        is_text = self._mode() == MODE_TEXT
        self.payload_edit.setVisible(is_text)
        self.load_text_btn.setVisible(is_text)
        self.secret.setVisible(not is_text)
        self._refresh_budget()

    def _update_steps(self, *_):
        self.step1.set_done(self._carrier_kind is not None)
        if self._mode() == MODE_TEXT:
            has_secret = bool(self.payload_edit.toPlainText())
        else:
            has_secret = bool(self.secret.path)
        self.step2.set_done(has_secret and self._fits())
        self.step3.set_done(bool(self.key.text()))

    def _suggest_key(self):
        self.key.setText(PasswordProtection().generate_password())
        self.key.toggle.setChecked(True)
        self.banner.show_message(
            "info", "Password generated. Copy it somewhere safe — "
            "there's no way to get it back from the file.",
            "Copy", self._copy_key)

    def _copy_key(self):
        QtWidgets.QApplication.clipboard().setText(self.key.text())
        self.banner.show_message("success", "Password copied to the clipboard.")

    def _describe_cipher(self):
        self.protection_note.setText(PROTECTION[self.cipher_combo.currentIndex()][2])

    def _on_cipher_changed(self):
        self._describe_cipher()
        self._refresh_budget()

    # -- carrier -------------------------------------------------------

    def _on_carrier_changed(self, path):
        if not self._ready:
            return
        self._carrier_kind = None
        self._carrier_size = (0, 0)
        self.banner.clear()
        if not path:
            self._refresh_budget()
            return

        name = os.path.basename(path)
        extension = os.path.splitext(path)[1].lower()
        size = theme.human_bytes(os.path.getsize(path)) if os.path.exists(path) else ""
        card = self.carrier.card

        if extension in IMAGE_CARRIERS:
            try:
                self._bits = TextSteganography.capacity_bits(path)
                from PIL import Image
                with Image.open(path) as image:
                    self._carrier_size = image.size
            except Exception as exc:
                card.set_file(name, size, icon_name="image")
                card.set_badge("Can't read this picture", "danger")
                self.banner.show_message("error", "That picture couldn't be opened: %s" % exc)
                self._refresh_budget()
                return
            self._carrier_kind = "image"
            card.set_file(name, "PNG picture · %d × %d · %s"
                          % (self._carrier_size + (size,)), thumb_path=path)
            card.set_badge("")
        elif extension in AUDIO_CARRIERS:
            self._carrier_kind = "audio"
            card.set_file(name, "MP3 song · %s" % size, icon_name="music")
            card.set_badge("Text messages only", "neutral")
        else:
            card.set_file(name, size)
            card.set_badge("Not supported — choose a .png or .mp3 file", "danger")

        self._refresh_budget()

    def _on_secret_changed(self, path):
        if path:
            name = os.path.basename(path)
            try:
                from PIL import Image
                with Image.open(path) as image:
                    w, h = image.size
                details = "%d × %d · %s" % (
                    w, h, theme.human_bytes(os.path.getsize(path)))
                self.secret.card.set_file(name, details, thumb_path=path)
                self.secret.card.set_badge("")
            except Exception:
                self.secret.card.set_file(name, "", icon_name="image")
                self.secret.card.set_badge("Can't read this picture", "danger")
        self._refresh_budget()

    def _load_text_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window(), "Load text from a file", "",
            "Text files (*.txt);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.payload_edit.setPlainText(handle.read())
        except Exception as exc:
            self.banner.show_message("error", "Couldn't read that file: %s" % exc)

    # -- space budget --------------------------------------------------

    def _used_bits(self):
        if self._mode() == MODE_TEXT:
            return capacity.embedded_bits(self.payload_edit.toPlainText(), self._cipher())
        secret = self.secret.path
        if secret and os.path.exists(secret):
            try:
                from PIL import Image
                with Image.open(secret) as image:
                    return capacity.image_payload_bits(*image.size)
            except Exception:
                return 0
        return 0

    def _fits(self):
        if self._carrier_kind != "image" or self._mode() != MODE_TEXT:
            return True
        total = capacity.image_capacity_bits(*self._carrier_size)
        return self._used_bits() <= total

    def _refresh_budget(self, *_):
        if not self._ready:
            return
        self._update_steps()
        mode = self._mode()
        algo = self._cipher()

        if self._carrier_kind is None:
            self.usage_box.hide()
            return
        self.usage_box.show()

        if self._carrier_kind == "audio":
            self.meter.hide()
            self.usage_value.setText("")
            if mode == MODE_IMAGE:
                self.usage_note.setText(
                    "<span style='color:%s'>Pictures can only be hidden inside a "
                    "PNG. Choose a PNG in step 1, or switch to a text message.</span>"
                    % theme.WARN)
            else:
                self.usage_note.setText(
                    "Songs store the message in their info tag, so there's no "
                    "size limit to worry about.")
            return

        self.meter.show()
        used = self._used_bits()
        total = capacity.image_capacity_bits(*self._carrier_size)
        ratio = (float(used) / total) if total else 0.0
        pct = ratio * 100
        if mode == MODE_IMAGE and ratio > 1.0:
            # An oversized picture is scaled down to fit, so it fills the
            # space rather than overflowing it.
            self.meter.set_ratio(1.0)
            self.usage_value.setText("100% (shrunk to fit)")
        else:
            self.meter.set_ratio(ratio)
            self.usage_value.setText(
                "<1%" if 0 < pct < 1 else "%d%%" % round(pct))

        if mode == MODE_TEXT:
            room = capacity.max_plaintext_bytes(total, algo)
            if ratio > 1.0:
                self.usage_note.setText(
                    "<span style='color:%s'>Too long for this picture. Shorten it "
                    "to about %s, or choose a bigger picture.</span>"
                    % (theme.DANGER, theme.human_bytes(room)))
            else:
                self.usage_note.setText(
                    "This picture can hold about %s of text." % theme.human_bytes(room))
        else:
            if ratio > 1.0:
                self.usage_note.setText(
                    "Your picture is bigger than the space available, so it will "
                    "be shrunk to fit. Hidden pictures are not encrypted \u2014 "
                    "the password only protects text.")
            else:
                self.usage_note.setText(
                    "Note: hidden pictures are not encrypted — the password "
                    "only protects text.")

    # -- embed ---------------------------------------------------------

    def _start_embed(self):
        if self._worker is not None and self._worker.isRunning():
            return

        carrier = self.carrier.path
        if not carrier or not os.path.exists(carrier):
            return self._fail("Choose a picture or song first (step 1).")
        if self._carrier_kind is None:
            return self._fail("That file type isn't supported. Choose a .png or .mp3 file.")

        mode = self._mode()
        text = self.payload_edit.toPlainText()
        secret = self.secret.path

        if mode == MODE_TEXT and not text:
            return self._fail("Write the message you want to hide (step 2).")
        if mode == MODE_IMAGE:
            if not secret or not os.path.exists(secret):
                return self._fail("Choose the picture you want to hide (step 2).")
            if self._carrier_kind != "image":
                return self._fail("Pictures can only be hidden inside a PNG.")
        if not self._fits():
            return self._fail("The message is too long for this picture.")

        suffix = os.path.splitext(carrier)[1] or ".png"
        stem = os.path.splitext(os.path.basename(carrier))[0]
        suggested = os.path.join(os.path.dirname(carrier), stem + "_hidden" + suffix)
        file_filter = ("MP3 song (*.mp3)" if suffix.lower() == ".mp3"
                       else "PNG picture (*.png)")
        output, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window(), "Save the file with your secret inside", suggested,
            file_filter + ";;All files (*)")
        if not output:
            return
        if os.path.abspath(output) == os.path.abspath(carrier):
            return self._fail("Save under a different name — overwriting the "
                              "original would destroy it.")

        payload = text if mode == MODE_TEXT else secret
        args = (carrier, payload, self.key.text(), self._cipher(), output)

        self.embed_btn.setEnabled(False)
        self.embed_btn.setText("Hiding…")
        self.banner.show_message("busy", "Hiding your secret inside %s…"
                                 % os.path.basename(carrier))

        self._worker = EmbedWorker(mode, args)
        self._worker.finished_ok.connect(self._on_embedded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        self.embed_btn.setEnabled(True)
        self.embed_btn.setText("Hide and save…")
        self._worker = None

    def _on_embedded(self, output):
        self._last_output = output
        self.banner.show_message(
            "success", "Done! Saved as <b>%s</b>. It opens like any normal file."
            % os.path.basename(output), "Show in folder", self._open_folder)

    def _on_failed(self, message):
        self.banner.show_message("error", "Something went wrong: %s" % message)

    def _fail(self, message):
        self.banner.show_message("warn", message)

    def _open_folder(self):
        if self._last_output and os.path.exists(self._last_output):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(
                os.path.dirname(os.path.abspath(self._last_output))))


class Ui_MainWindow(object):
    """Lets the page run on its own in a QMainWindow."""

    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setWindowTitle("Whisper — Hide a message")
        MainWindow.resize(880, 820)
        self.page = HidePage()
        MainWindow.setCentralWidget(self.page)

    def retranslateUi(self, MainWindow):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    theme.apply(app)
    window = QtWidgets.QMainWindow()
    Ui_MainWindow().setupUi(window)
    window.show()
    sys.exit(app.exec_())
