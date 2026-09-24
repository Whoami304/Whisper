"""The Hide window: put a payload inside a carrier file.

Rewritten from the generated Qt Designer version. That one laid the
window out as a converter -- two boxes with an arrow between them and a
"Convert" button -- which described the wrong job: it said nothing about
how much room the carrier had, what the key was for, which cipher was in
use (the code hard-coded "Strong" and the window never mentioned it), or
whether the last operation had worked. Every widget was positioned with
setGeometry at a fixed 900x700, so nothing reflowed and the lower half of
the window was unreachable on a short screen.

The layout now follows the order the work actually happens in, which is
also the order the stages are numbered:

    01 CARRIER -> 02 PAYLOAD -> 03 CONFIGURATION -> 04 OPERATION -> 05 RESULT

Each stage answers one question, and the stage above it has to be
answered first, so the window reads top to bottom without instructions.
"""

import os
import sys
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

import gui  # sets sys.path for both the GUI and the engine

from gui import capacity, theme
# Flat imports, matching how the engine imports itself: going through
# the Whisper package would create a second copy of every engine
# module, and its StegoError would be a different class from the one
# the engine raises.
from protection import PasswordProtection
from StegoTextPass import StegoTextPass
from steganography import TextSteganography

MODE_TEXT = "text"
MODE_IMAGE = "image"

IMAGE_CARRIERS = (".png",)
AUDIO_CARRIERS = (".mp3",)

CIPHERS = [
    ("Strong  -  AES-256-CBC", "Strong"),
    ("Medium  -  hex transform", "Medium"),
    ("Weak  -  character shift", "Weak"),
]


class EmbedWorker(QtCore.QThread):
    """Runs one embed off the UI thread.

    The old window called the engine directly from the button handler, so
    a large carrier froze the window with no way to tell whether it had
    crashed or was still working.
    """

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


class Ui_MainWindow(object):
    """Kept as Ui_MainWindow with setupUi() so the start window's
    navigation keeps working unchanged."""

    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        self._worker = None
        self._ready = False
        self._carrier_kind = None
        self._carrier_size = (0, 0)
        self._last_output = ""

        MainWindow.setObjectName("HideWindow")
        MainWindow.setWindowTitle("Whisper - Hide Content")
        MainWindow.resize(940, 760)
        MainWindow.setMinimumSize(720, 520)
        MainWindow.setAcceptDrops(True)
        MainWindow.dragEnterEvent = self._drag_enter
        MainWindow.dropEvent = self._drop

        page = theme.scrollable(MainWindow)
        head, self.chip = theme.masthead(
            "WHISPER  //  EMBED",
            "Hide data inside an ordinary file",
            "The payload is written into the least significant bits of a PNG, "
            "or into an MP3 tag. The result opens normally in any viewer.")
        page.addLayout(head)
        page.addWidget(self._carrier_stage())
        page.addWidget(self._payload_stage())
        page.addWidget(self._config_stage())
        page.addWidget(self._operation_stage())
        page.addWidget(self._result_stage())
        page.addStretch()

        self._ready = True
        self._sync_mode()
        self._refresh_budget()
        self._log("Ready. Choose a carrier to begin.")

    # -- stage 01 ------------------------------------------------------

    def _carrier_stage(self):
        frame, content = theme.module("01", "CARRIER")

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.carrier_input = QtWidgets.QLineEdit()
        self.carrier_input.setPlaceholderText(
            "Path to a .png or .mp3 file, or drop one on this window")
        self.carrier_input.textChanged.connect(self._on_carrier_changed)
        row.addWidget(self.carrier_input, 1)
        browse = QtWidgets.QPushButton("BROWSE")
        browse.clicked.connect(self._browse_carrier)
        row.addWidget(browse)
        content.addLayout(row)

        meta = QtWidgets.QHBoxLayout()
        meta.setSpacing(26)
        kind_box, self.out_kind = theme.readout("TYPE")
        dims_box, self.out_dims = theme.readout("DIMENSIONS")
        size_box, self.out_size = theme.readout("FILE SIZE")
        cap_box, self.out_capacity = theme.readout("CAPACITY")
        for box in (kind_box, dims_box, size_box, cap_box):
            meta.addLayout(box)
        meta.addStretch()
        content.addLayout(meta)
        return frame

    # -- stage 02 ------------------------------------------------------

    def _payload_stage(self):
        frame, content = theme.module("02", "PAYLOAD")

        switch = QtWidgets.QHBoxLayout()
        switch.setSpacing(6)
        self.mode_text = QtWidgets.QRadioButton("TEXT")
        self.mode_image = QtWidgets.QRadioButton("IMAGE FILE")
        self.mode_text.setChecked(True)
        group = QtWidgets.QButtonGroup(self.MainWindow)
        group.addButton(self.mode_text)
        group.addButton(self.mode_image)
        self._mode_group = group
        self.mode_text.toggled.connect(self._sync_mode)
        switch.addWidget(self.mode_text)
        switch.addWidget(self.mode_image)
        switch.addStretch()
        self.load_text_btn = QtWidgets.QPushButton("LOAD FROM FILE")
        self.load_text_btn.setObjectName("ghost")
        self.load_text_btn.clicked.connect(self._load_text_file)
        switch.addWidget(self.load_text_btn)
        content.addLayout(switch)

        self.payload_edit = QtWidgets.QPlainTextEdit()
        self.payload_edit.setPlaceholderText("Type or paste the text to hide...")
        self.payload_edit.setFixedHeight(110)
        self.payload_edit.textChanged.connect(self._refresh_budget)
        content.addWidget(self.payload_edit)

        self.secret_row = QtWidgets.QWidget()
        secret_layout = QtWidgets.QHBoxLayout(self.secret_row)
        secret_layout.setContentsMargins(0, 0, 0, 0)
        secret_layout.setSpacing(8)
        self.secret_input = QtWidgets.QLineEdit()
        self.secret_input.setPlaceholderText("Path to the .png to hide")
        self.secret_input.textChanged.connect(self._refresh_budget)
        secret_layout.addWidget(self.secret_input, 1)
        secret_browse = QtWidgets.QPushButton("BROWSE")
        secret_browse.clicked.connect(self._browse_secret)
        secret_layout.addWidget(secret_browse)
        content.addWidget(self.secret_row)

        meta = QtWidgets.QHBoxLayout()
        meta.setSpacing(26)
        plain_box, self.out_plain = theme.readout("PLAINTEXT", "0 B")
        cipher_box, self.out_cipher = theme.readout("AFTER CIPHER", "0 B")
        bits_box, self.out_bits = theme.readout("BITS USED", "0")
        for box in (plain_box, cipher_box, bits_box):
            meta.addLayout(box)
        meta.addStretch()
        content.addLayout(meta)

        self.payload_note = QtWidgets.QLabel("")
        self.payload_note.setObjectName("note")
        self.payload_note.setWordWrap(True)
        content.addWidget(self.payload_note)
        return frame

    # -- stage 03 ------------------------------------------------------

    def _config_stage(self):
        frame, content = theme.module("03", "CONFIGURATION")

        content.addWidget(theme.micro_label("KEY"))
        key_row = QtWidgets.QHBoxLayout()
        key_row.setSpacing(8)
        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.key_input.setPlaceholderText(
            "The key needed to recover this payload")
        key_row.addWidget(self.key_input, 1)
        self.reveal_btn = QtWidgets.QPushButton("SHOW")
        self.reveal_btn.setCheckable(True)
        self.reveal_btn.toggled.connect(self._toggle_key)
        key_row.addWidget(self.reveal_btn)
        suggest = QtWidgets.QPushButton("SUGGEST")
        suggest.clicked.connect(self._suggest_key)
        key_row.addWidget(suggest)
        content.addLayout(key_row)

        cipher_row = QtWidgets.QHBoxLayout()
        cipher_col = QtWidgets.QVBoxLayout()
        cipher_col.setSpacing(4)
        cipher_col.addWidget(theme.micro_label("CIPHER"))
        self.cipher_combo = QtWidgets.QComboBox()
        for label, value in CIPHERS:
            self.cipher_combo.addItem(label, value)
        self.cipher_combo.setFixedWidth(240)
        self.cipher_combo.currentIndexChanged.connect(self._on_cipher_changed)
        cipher_col.addWidget(self.cipher_combo)
        cipher_row.addLayout(cipher_col)
        cipher_row.addStretch()
        content.addLayout(cipher_row)

        self.protection_note = QtWidgets.QLabel("")
        self.protection_note.setObjectName("noteCaution")
        self.protection_note.setWordWrap(True)
        content.addWidget(self.protection_note)
        self._describe_cipher()
        return frame

    # -- stage 04 ------------------------------------------------------

    def _operation_stage(self):
        frame, content = theme.module("04", "OPERATION")

        head = QtWidgets.QHBoxLayout()
        head.addWidget(theme.micro_label("CAPACITY ALLOCATION"))
        head.addStretch()
        self.budget_value = QtWidgets.QLabel("--")
        self.budget_value.setObjectName("readoutValue")
        head.addWidget(self.budget_value)
        content.addLayout(head)

        self.meter = theme.CapacityMeter()
        content.addWidget(self.meter)

        self.budget_note = QtWidgets.QLabel("")
        self.budget_note.setObjectName("note")
        self.budget_note.setWordWrap(True)
        content.addWidget(self.budget_note)

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)
        self.embed_btn = QtWidgets.QPushButton("EMBED PAYLOAD")
        self.embed_btn.setObjectName("primary")
        self.embed_btn.clicked.connect(self._start_embed)
        actions.addWidget(self.embed_btn)
        actions.addStretch()
        self.back_btn = QtWidgets.QPushButton("BACK")
        self.back_btn.setObjectName("ghost")
        self.back_btn.clicked.connect(self._go_back)
        actions.addWidget(self.back_btn)
        content.addLayout(actions)
        return frame

    # -- stage 05 ------------------------------------------------------

    def _result_stage(self):
        frame, content = theme.module("05", "RESULT")

        status_row = QtWidgets.QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(theme.micro_label("STATUS"))
        self.status_label = QtWidgets.QLabel("Nothing embedded yet.")
        self.status_label.setObjectName("note")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        content.addLayout(status_row)

        out_row = QtWidgets.QHBoxLayout()
        out_row.setSpacing(8)
        self.output_display = QtWidgets.QLineEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setPlaceholderText(
            "The finished file's path appears here")
        out_row.addWidget(self.output_display, 1)
        self.open_btn = QtWidgets.QPushButton("OPEN FOLDER")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_folder)
        out_row.addWidget(self.open_btn)
        content.addLayout(out_row)

        content.addWidget(theme.micro_label("OPERATION LOG"))
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(92)
        content.addWidget(self.log_view)
        return frame

    # -- helpers -------------------------------------------------------

    def _log(self, message):
        """One timestamped line. Never receives a key or a payload."""
        self.log_view.appendPlainText(
            "%s  %s" % (datetime.now().strftime("%H:%M:%S"), message))

    def _mode(self):
        return MODE_TEXT if self.mode_text.isChecked() else MODE_IMAGE

    def _cipher(self):
        return self.cipher_combo.itemData(self.cipher_combo.currentIndex())

    def _sync_mode(self):
        if not self._ready:
            return
        is_text = self._mode() == MODE_TEXT
        self.payload_edit.setVisible(is_text)
        self.load_text_btn.setVisible(is_text)
        self.secret_row.setVisible(not is_text)
        self._refresh_budget()

    def _toggle_key(self, shown):
        self.key_input.setEchoMode(
            QtWidgets.QLineEdit.Normal if shown else QtWidgets.QLineEdit.Password)
        self.reveal_btn.setText("HIDE" if shown else "SHOW")

    def _suggest_key(self):
        key = PasswordProtection().generate_password()
        self.key_input.setText(key)
        self.reveal_btn.setChecked(True)
        self._log("Key suggested. Copy it now -- it cannot be recovered "
                  "from the output file.")

    def _describe_cipher(self):
        if self._cipher() == "Strong":
            self.protection_note.setText(
                "AES-256-CBC. The key check is an unsalted SHA-256, so a file "
                "someone already holds can be attacked offline.")
        else:
            self.protection_note.setText(
                "Obfuscation only -- this cipher hides the text from a casual "
                "reader and is not encryption. Use Strong for AES-256.")

    def _on_cipher_changed(self):
        self._describe_cipher()
        self._refresh_budget()

    # -- carrier -------------------------------------------------------

    def _on_carrier_changed(self):
        if not self._ready:
            return
        path = self.carrier_input.text().strip().strip('"')
        self._carrier_kind = None
        self._carrier_size = (0, 0)

        if not path:
            for label in (self.out_kind, self.out_dims, self.out_size,
                          self.out_capacity):
                label.setText("--")
            self._refresh_budget()
            return

        extension = os.path.splitext(path)[1].lower()
        if not os.path.exists(path):
            self.out_kind.setText("NOT FOUND")
            for label in (self.out_dims, self.out_size, self.out_capacity):
                label.setText("--")
            self._refresh_budget()
            return

        self.out_size.setText(theme.human_bytes(os.path.getsize(path)))

        if extension in IMAGE_CARRIERS:
            try:
                bits = TextSteganography.capacity_bits(path)
                from PIL import Image
                with Image.open(path) as image:
                    self._carrier_size = image.size
            except Exception as exc:
                self.out_kind.setText("UNREADABLE")
                self.out_dims.setText("--")
                self.out_capacity.setText("--")
                self.status_label.setText("Carrier could not be read: %s" % exc)
                self._refresh_budget()
                return
            self._carrier_kind = "image"
            self.out_kind.setText("PNG IMAGE")
            self.out_dims.setText("%d x %d" % self._carrier_size)
            self.out_capacity.setText(theme.human_bytes(bits // 8))
        elif extension in AUDIO_CARRIERS:
            self._carrier_kind = "audio"
            self.out_kind.setText("MP3 AUDIO")
            self.out_dims.setText("--")
            self.out_capacity.setText("TAG-BASED")
        else:
            self.out_kind.setText("UNSUPPORTED")
            self.out_dims.setText("--")
            self.out_capacity.setText("--")

        self._refresh_budget()

    def _browse_carrier(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.MainWindow, "Select carrier file", "",
            "Carrier files (*.png *.mp3);;PNG image (*.png);;"
            "MP3 audio (*.mp3);;All files (*)")
        if path:
            self.carrier_input.setText(os.path.abspath(path))

    def _browse_secret(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.MainWindow, "Select the image to hide", "",
            "PNG image (*.png);;All files (*)")
        if path:
            self.secret_input.setText(os.path.abspath(path))

    def _load_text_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.MainWindow, "Load payload text", "",
            "Text files (*.txt);;All files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.payload_edit.setPlainText(handle.read())
            self._log("Loaded payload text from %s" % os.path.basename(path))
        except Exception as exc:
            self.status_label.setText("Could not read that file: %s" % exc)

    # -- budget --------------------------------------------------------

    def _refresh_budget(self):
        """Recomputes the readouts and the meter.

        Measures the ciphertext, so the meter cannot promise a fit that
        the engine will then refuse.
        """
        if not self._ready:
            return

        mode = self._mode()
        algo = self._cipher()

        if mode == MODE_TEXT:
            text = self.payload_edit.toPlainText()
            plain = len(text.encode("utf-8"))
            after = capacity.ciphertext_length(text, algo)
            used = capacity.embedded_bits(text, algo)
            self.out_plain.setText(theme.human_bytes(plain))
            self.out_cipher.setText(theme.human_bytes(after))
            self.out_bits.setText(str(used))
            if plain and after > plain:
                self.payload_note.setText(
                    "This cipher expands the payload from %s to %s before it is "
                    "embedded, so the budget below counts the larger figure."
                    % (theme.human_bytes(plain), theme.human_bytes(after)))
            else:
                self.payload_note.setText("")
        else:
            secret = self.secret_input.text().strip().strip('"')
            used = 0
            if secret and os.path.exists(secret):
                try:
                    from PIL import Image
                    with Image.open(secret) as image:
                        used = capacity.image_payload_bits(*image.size)
                    self.out_plain.setText(
                        theme.human_bytes(os.path.getsize(secret)))
                except Exception:
                    self.out_plain.setText("UNREADABLE")
            else:
                self.out_plain.setText("--")
            self.out_cipher.setText("RAW PIXELS")
            self.out_bits.setText(str(used))
            self.payload_note.setText(
                "An image payload is stored as raw pixels and is not encrypted; "
                "the key controls access to the file. One too large for the "
                "carrier is scaled down to fit rather than refused.")

        if self._carrier_kind is None:
            self.meter.set_unknown()
            self.budget_value.setText("--")
            self.budget_note.setText("Choose a carrier to see its capacity.")
            return

        if self._carrier_kind == "audio":
            self.meter.set_unknown()
            self.budget_value.setText("NOT APPLICABLE")
            self.budget_note.setText(
                "An MP3 carries the payload in an ID3 tag, which has no fixed "
                "pixel budget. A very large payload still inflates the file.")
            return

        width, height = self._carrier_size
        total = capacity.image_capacity_bits(width, height)
        ratio = (float(used) / total) if total else 0.0
        self.meter.set_ratio(ratio)
        self.budget_value.setText("%s / %s   %.1f%%" % (
            theme.human_bytes(used // 8), theme.human_bytes(total // 8),
            ratio * 100))

        if mode == MODE_TEXT:
            room = capacity.max_plaintext_bytes(total, algo)
            if ratio > 1.0:
                self.budget_note.setText(
                    "Over capacity. This carrier holds about %s of text with "
                    "the %s cipher." % (theme.human_bytes(room), algo))
            else:
                self.budget_note.setText(
                    "Room for about %s of text with the %s cipher."
                    % (theme.human_bytes(room), algo))
        else:
            self.budget_note.setText(
                "An oversized image is scaled down to fit this carrier.")

    # -- drag and drop -------------------------------------------------

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path:
            return
        if self._mode() == MODE_IMAGE and self.carrier_input.text().strip():
            self.secret_input.setText(os.path.abspath(path))
        else:
            self.carrier_input.setText(os.path.abspath(path))

    # -- embed ---------------------------------------------------------

    def _start_embed(self):
        carrier = self.carrier_input.text().strip().strip('"')
        if not carrier or not os.path.exists(carrier):
            self._fail("Choose a carrier file first.")
            return
        if self._carrier_kind is None:
            self._fail("That carrier is not a .png or .mp3 file.")
            return

        mode = self._mode()
        text = self.payload_edit.toPlainText()
        secret = self.secret_input.text().strip().strip('"')

        if mode == MODE_TEXT and not text:
            self._fail("The payload is empty -- there is nothing to hide.")
            return
        if mode == MODE_IMAGE:
            if not secret or not os.path.exists(secret):
                self._fail("Choose the image to hide.")
                return
            if self._carrier_kind != "image":
                self._fail("Hiding an image needs a .png carrier.")
                return

        suffix = os.path.splitext(carrier)[1] or ".png"
        stem = os.path.splitext(os.path.basename(carrier))[0]
        suggested = os.path.join(os.path.dirname(carrier), stem + "_hidden" + suffix)
        output, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.MainWindow, "Save the carrier with the payload", suggested,
            "PNG image (*.png);;MP3 audio (*.mp3);;All files (*)")
        if not output:
            return
        if os.path.abspath(output) == os.path.abspath(carrier):
            self._fail("Choose a different output file: writing over the "
                       "carrier would destroy the original.")
            return

        if mode == MODE_TEXT:
            args = (carrier, text, self.key_input.text(), self._cipher(), output)
        else:
            args = (carrier, secret, self.key_input.text(), self._cipher(), output)

        self.embed_btn.setEnabled(False)
        theme.set_chip(self.chip, "EMBEDDING", theme.SIGNAL)
        self.status_label.setText("Embedding into %s..." % os.path.basename(carrier))
        self._log("EMBED  carrier=%s  cipher=%s  mode=%s"
                  % (os.path.basename(carrier), self._cipher(), mode))
        self.output_display.clear()
        self.open_btn.setEnabled(False)

        self._worker = EmbedWorker(mode, args)
        self._worker.finished_ok.connect(self._on_embedded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(lambda: self.embed_btn.setEnabled(True))
        self._worker.start()

    def _on_embedded(self, output):
        self._last_output = output
        theme.set_chip(self.chip, "EMBEDDED", theme.OKAY)
        self.status_label.setText(
            "Payload embedded. The file opens normally in any viewer.")
        self.output_display.setText(output)
        self.open_btn.setEnabled(True)
        try:
            size = theme.human_bytes(os.path.getsize(output))
        except OSError:
            size = "unknown size"
        self._log("Wrote %s (%s)" % (os.path.basename(output), size))

    def _on_failed(self, message):
        theme.set_chip(self.chip, "FAILED", theme.ALERT)
        self.status_label.setText(message)
        self._log("FAILED  %s" % message)

    def _fail(self, message):
        """A refusal that never started an operation."""
        theme.set_chip(self.chip, "BLOCKED", theme.CAUTION)
        self.status_label.setText(message)

    # -- result --------------------------------------------------------

    def _open_folder(self):
        if self._last_output and os.path.exists(self._last_output):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(
                os.path.dirname(os.path.abspath(self._last_output))))

    def _go_back(self):
        """Returns to the start window instead of leaving the user stranded.

        The old windows closed the start window on the way here and gave
        no way back, so the only route to the other operation was to
        restart the app.
        """
        from gui.StartWindow.mainWindow import Ui_MainWindow as StartUI
        self._start_window = QtWidgets.QMainWindow()
        self._start_ui = StartUI()
        self._start_ui.setupUi(self._start_window)
        self._start_window.show()
        self.MainWindow.close()

    def retranslateUi(self, MainWindow):
        """Kept for compatibility with the generated-code call pattern."""
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    theme.apply(app)
    window = QtWidgets.QMainWindow()
    Ui_MainWindow().setupUi(window)
    window.show()
    sys.exit(app.exec_())
