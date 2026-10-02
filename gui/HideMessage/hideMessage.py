"""The Hide page: put a text message or a picture inside a picture or song.

Three steps -- choose a file, choose what to hide, set a password -- and
one button that saves a copy with the secret inside. All the work is done
by Whisper/engine.py on a QThread, so the window never freezes, and a
second click while one is running is ignored.
"""

import html
import os
import sys

if __package__ in (None, ""):          # started as a script, e.g. from PyCharm
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import gui  # sets sys.path and checks/repairs dependencies -- keep before PyQt5

from PyQt5 import QtCore, QtGui, QtWidgets

import engine
from gui import theme

MODE_TEXT = "text"
MODE_IMAGE = "image"

CARRIER_FILTER = ("Pictures and audio (*.png *.bmp *.tif *.tiff *.jpg *.jpeg *.webp *.wav *.mp3);;"
                  "Pictures (*.png *.bmp *.tif *.tiff *.jpg *.jpeg *.webp);;"
                  "WAV audio (*.wav);;MP3 audio (*.mp3);;All files (*)")
SECRET_FILTER = "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff);;All files (*)"

KIND_LABEL = {"image": "Picture", "wav": "WAV audio", "mp3": "MP3 audio"}


class EmbedWorker(QtCore.QThread):
    """Runs one hide operation off the UI thread."""

    finished_ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, mode, carrier, payload, password, output, parent=None):
        super(EmbedWorker, self).__init__(parent)
        self.mode, self.carrier, self.payload = mode, carrier, payload
        self.password, self.output = password, output

    def run(self):
        try:
            if self.mode == MODE_TEXT:
                engine.hide_text(self.carrier, self.output, self.payload, self.password)
            else:
                engine.hide_image(self.carrier, self.output, self.payload, self.password)
            self.finished_ok.emit(self.output)
        except engine.WhisperError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                      # never let a worker die silently
            self.failed.emit("Unexpected error: %s" % exc)


class HidePage(theme.Page):

    def __init__(self, on_back=None, parent=None):
        super(HidePage, self).__init__("Hide a message", on_back, parent)
        self._worker = None
        self._ready = False
        self._carrier_kind = None
        self._capacity = None          # bytes, None = no practical limit (MP3)
        self._last_output = ""

        self.column.addWidget(self._carrier_step())
        self.column.addWidget(self._secret_step())
        self.column.addWidget(self._password_step())
        self.column.addStretch()

        self.banner = theme.Banner()
        self.actions.addWidget(self.banner, 1)
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
            1, "Choose a picture or audio file",
            "The secret goes inside a copy of this file. The copy looks and "
            "sounds the same; your original is not changed.")
        self.carrier = theme.FilePicker(
            "Drop a picture, WAV or MP3 here", "or click to browse",
            "Choose a picture or audio file", CARRIER_FILTER)
        self.carrier.fileChanged.connect(self._on_carrier_changed)
        self.step1.body.addWidget(self.carrier)
        return self.step1

    # -- step 2 --------------------------------------------------------

    def _secret_step(self):
        self.step2 = theme.StepCard(2, "What do you want to hide?")

        top = QtWidgets.QHBoxLayout()
        self.mode = theme.Segmented([("Text message", "text"), ("Picture", "image")])
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
            "Drop the picture to hide", "PNG, JPG, BMP, GIF… · or click to browse",
            "Choose the picture to hide", SECRET_FILTER, icon_name="image", height=120)
        self.secret.fileChanged.connect(self._on_secret_changed)
        self.step2.body.addWidget(self.secret)

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
            "You'll need this exact password to read the secret later. "
            "It can't be recovered if you forget it.")

        self.key = theme.PasswordField("Choose a password")
        self.key.edit.textChanged.connect(self._on_password_changed)
        suggest = QtWidgets.QPushButton("Generate")
        suggest.setToolTip("Create a strong random password")
        suggest.clicked.connect(self._suggest_key)
        self.key.row.addWidget(suggest)
        self.strength = theme.StrengthMeter()
        self.step3.body.addLayout(theme.field(
            "Password", self.key,
            theme.label("Encrypted with AES-256-GCM. The key is derived from your "
                        "password with scrypt, so each guess is slow — but a long, "
                        "random password is still what keeps it safe.", "hint", wrap=True)))
        self.step3.body.addWidget(self.strength)
        return self.step3

    # -- helpers -------------------------------------------------------

    def _mode(self):
        return MODE_TEXT if self.mode.index() == 0 else MODE_IMAGE

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
        has_secret = (bool(self.payload_edit.toPlainText()) if self._mode() == MODE_TEXT
                      else bool(self.secret.path))
        self.step2.set_done(has_secret and self._fits())
        self.step3.set_done(bool(self.key.text()))

    def _on_password_changed(self, text):
        self.strength.set_score(*engine.password_strength(text))
        self._update_steps()

    def _suggest_key(self):
        self.key.setText(engine.generate_password())
        self.key.toggle.setChecked(True)
        self.banner.show_message(
            "info", "Password generated. Save it somewhere safe — there's no way "
            "to get it back from the file.", "Copy", self._copy_key)

    def _copy_key(self):
        QtWidgets.QApplication.clipboard().setText(self.key.text())
        self.banner.show_message("success", "Password copied to the clipboard.")

    # -- carrier -------------------------------------------------------

    def _on_carrier_changed(self, path):
        if not self._ready:
            return
        self._carrier_kind = None
        self._capacity = None
        self.banner.clear()
        if not path:
            self._refresh_budget()
            return

        name = os.path.basename(path)
        size = theme.human_bytes(os.path.getsize(path)) if os.path.exists(path) else ""
        card = self.carrier.card
        kind = engine.carrier_kind(path)
        if kind is None:
            card.set_file(name, size)
            card.set_badge("Not supported — choose a picture, WAV or MP3", "danger")
            self._refresh_budget()
            return
        try:
            self._capacity = engine.capacity(path)
        except engine.WhisperError as exc:
            card.set_file(name, size, icon_name="image" if kind == "image" else "music")
            card.set_badge("Can't read this file", "danger")
            self.banner.show_message("error", html.escape(str(exc)))
            self._refresh_budget()
            return

        self._carrier_kind = kind
        if kind == "image":
            from PIL import Image
            with Image.open(path) as image:
                dims = "%d × %d" % image.size
            card.set_file(name, "Picture · %s · %s" % (dims, size), thumb_path=path)
            lossy = os.path.splitext(path)[1].lower() not in engine.LOSSLESS_IMAGE_EXTENSIONS
            card.set_badge("Will be saved as PNG" if lossy else "", "neutral")
        elif kind == "wav":
            card.set_file(name, "WAV audio · %s" % size, icon_name="music")
            card.set_badge("")
        else:
            card.set_file(name, "MP3 audio · %s" % size, icon_name="music")
            card.set_badge("Stored in the file's tag", "warn")
        self._refresh_budget()

    def _on_secret_changed(self, path):
        if path:
            name = os.path.basename(path)
            try:
                from PIL import Image
                with Image.open(path) as image:
                    w, h = image.size
                self.secret.card.set_file(
                    name, "%d × %d · %s" % (w, h, theme.human_bytes(os.path.getsize(path))),
                    thumb_path=path)
                self.secret.card.set_badge("")
            except Exception:
                self.secret.card.set_file(name, "", icon_name="image")
                self.secret.card.set_badge("Can't read this picture", "danger")
        self._refresh_budget()

    def _load_text_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window(), "Load text from a file", "", "Text files (*.txt);;All files (*)")
        if not path:
            return
        try:
            if os.path.getsize(path) > 50 * 1024 * 1024:
                raise ValueError("the file is larger than 50 MB")
            with open(path, "r", encoding="utf-8") as handle:
                self.payload_edit.setPlainText(handle.read())
        except UnicodeDecodeError:
            self.banner.show_message("error", "That file isn't UTF-8 text.")
        except Exception as exc:
            self.banner.show_message("error", "Couldn't read that file: %s" % html.escape(str(exc)))

    # -- space budget --------------------------------------------------

    def _used_bytes(self):
        if self._mode() == MODE_TEXT:
            return len(self.payload_edit.toPlainText().encode("utf-8"))
        secret = self.secret.path
        if secret and os.path.exists(secret):
            return os.path.getsize(secret)
        return 0

    def _fits(self):
        if self._capacity is None or self._mode() == MODE_IMAGE:
            return True            # MP3: no limit; pictures are shrunk to fit
        return self._used_bytes() <= self._capacity

    def _refresh_budget(self, *_):
        if not self._ready:
            return
        self._update_steps()
        if self._carrier_kind is None:
            self.usage_box.hide()
            return
        self.usage_box.show()

        if self._capacity is None:                     # MP3
            self.meter.hide()
            self.usage_value.setText("")
            self.usage_note.setText(
                "MP3 can't hide data in the sound itself, so the encrypted secret is "
                "stored in the file's tag. Nobody can read it without the password, "
                "but a tag editor can see that something is there. Use a WAV or a "
                "picture if that matters.")
            return

        self.meter.show()
        used, total = self._used_bytes(), self._capacity
        ratio = float(used) / total if total else 1.0
        if self._mode() == MODE_IMAGE and ratio > 1.0:
            self.meter.set_ratio(1.0)
            self.usage_value.setText("100% (shrunk to fit)")
            self.usage_note.setText(
                "The picture is bigger than the space available (%s), so it will be "
                "re-saved smaller to fit." % theme.human_bytes(total))
            return
        self.meter.set_ratio(ratio)
        pct = ratio * 100
        self.usage_value.setText("<1%" if 0 < pct < 1 else "%d%%" % round(pct))
        if ratio > 1.0:
            self.usage_note.setText(
                "<span style='color:%s'>Too long for this file: it holds about %s. "
                "Shorten the message or choose a bigger file.</span>"
                % (theme.DANGER, theme.human_bytes(total)))
        else:
            self.usage_note.setText("This file can hold about %s." % theme.human_bytes(total))

    # -- hide ----------------------------------------------------------

    def _start_embed(self):
        if self._worker is not None and self._worker.isRunning():
            return

        carrier = self.carrier.path
        if not carrier or not os.path.exists(carrier):
            return self._fail("Choose a picture or audio file first (step 1).")
        if self._carrier_kind is None:
            return self._fail("That file type isn't supported. Choose a picture, WAV or MP3.")

        mode = self._mode()
        text = self.payload_edit.toPlainText()
        secret = self.secret.path
        if mode == MODE_TEXT and not text:
            return self._fail("Write the message you want to hide (step 2).")
        if mode == MODE_IMAGE and (not secret or not os.path.exists(secret)):
            return self._fail("Choose the picture you want to hide (step 2).")
        if not self._fits():
            return self._fail("The message is too long for this file.")
        password = self.key.text()
        if not password:
            return self._fail("Choose a password (step 3).")
        if engine.password_strength(password)[0] <= 1:
            answer = QtWidgets.QMessageBox.question(
                self.window(), "Weak password",
                "This password is easy to guess, and anyone who gets the file can "
                "keep trying offline.\n\nUse it anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return

        suffix = engine.output_extension(carrier)
        stem = os.path.splitext(os.path.basename(carrier))[0]
        suggested = os.path.join(os.path.dirname(carrier), stem + "_hidden" + suffix)
        file_filter = {".png": "PNG picture (*.png)", ".wav": "WAV audio (*.wav)",
                       ".mp3": "MP3 audio (*.mp3)"}[suffix]
        output, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window(), "Save the file with your secret inside", suggested, file_filter)
        if not output:
            return
        if not output.lower().endswith(suffix):
            output += suffix
        if os.path.abspath(output) == os.path.abspath(carrier):
            return self._fail("Save under a different name — overwriting the original "
                              "would destroy it.")

        self.embed_btn.setEnabled(False)
        self.embed_btn.setText("Hiding…")
        self.banner.show_message("busy", "Hiding your secret inside %s…"
                                 % html.escape(os.path.basename(carrier)))
        payload = text if mode == MODE_TEXT else secret
        self._worker = EmbedWorker(mode, carrier, payload, password, output)
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
            % html.escape(os.path.basename(output)), "Show in folder", self._open_folder)

    def _on_failed(self, message):
        self.banner.show_message("error", html.escape(message))

    def _fail(self, message):
        self.banner.show_message("warn", message)

    def _open_folder(self):
        if self._last_output and os.path.exists(self._last_output):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(
                os.path.dirname(os.path.abspath(self._last_output))))


def main():
    app = QtWidgets.QApplication(sys.argv)
    theme.apply(app)
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Whisper — Hide a message")
    window.resize(880, 820)
    window.setCentralWidget(HidePage())
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
