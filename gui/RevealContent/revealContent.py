"""The Reveal page: read a secret hidden in a file made by Whisper.

Choose the file, enter the password, press Unlock. Whisper works out by
itself whether a text message or a picture was hidden. Without the right
password a Whisper file is indistinguishable from an ordinary one, so the
page never claims to know in advance whether a secret is present.

Extraction runs on a QThread so the window never freezes.
"""

import html
import io
import os
import sys

if __package__ in (None, ""):          # started as a script, e.g. from PyCharm
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import gui  # sets sys.path and checks/repairs dependencies -- keep before PyQt5

from PyQt5 import QtCore, QtGui, QtWidgets

import engine
from gui import theme

SOURCE_FILTER = ("Pictures and audio (*.png *.bmp *.tif *.tiff *.wav *.mp3);;"
                 "Pictures (*.png *.bmp *.tif *.tiff);;WAV audio (*.wav);;"
                 "MP3 audio (*.mp3);;All files (*)")

# PIL format name -> (extension, file-dialog filter)
_IMAGE_SAVE = {
    "PNG": (".png", "PNG picture (*.png)"),
    "JPEG": (".jpg", "JPEG picture (*.jpg *.jpeg)"),
    "GIF": (".gif", "GIF picture (*.gif)"),
    "BMP": (".bmp", "BMP picture (*.bmp)"),
    "WEBP": (".webp", "WebP picture (*.webp)"),
    "TIFF": (".tif", "TIFF picture (*.tif *.tiff)"),
}


class ExtractWorker(QtCore.QThread):
    """Runs one reveal off the UI thread."""

    recovered = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, path, password, parent=None):
        super(ExtractWorker, self).__init__(parent)
        self.path = path
        self.password = password

    def run(self):
        try:
            self.recovered.emit(engine.reveal(self.path, self.password))
        except engine.WhisperError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                      # never let a worker die silently
            self.failed.emit("Unexpected error: %s" % exc)


class RevealPage(theme.Page):

    def __init__(self, on_back=None, parent=None):
        super(RevealPage, self).__init__("Read a hidden message", on_back, parent)
        self._worker = None
        self._image_bytes = None
        self._image_format = "PNG"
        self._text = ""

        self.column.addWidget(self._source_step())
        self.column.addWidget(self._key_step())
        self.column.addWidget(self._result_card())
        self.column.addStretch()

        self.banner = theme.Banner()
        self.actions.addWidget(self.banner, 1)
        self.extract_btn = QtWidgets.QPushButton("Unlock")
        self.extract_btn.setObjectName("primary")
        self.extract_btn.setIcon(theme.icon("unlock", 16, "#ffffff"))
        self.extract_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.extract_btn.clicked.connect(self._start_extract)
        self.actions.addWidget(self.extract_btn, 0, QtCore.Qt.AlignRight)

    # -- step 1 --------------------------------------------------------

    def _source_step(self):
        self.step1 = theme.StepCard(
            1, "Choose the file with the secret",
            "A picture (PNG), WAV or MP3 that was saved with Whisper. "
            "Whisper detects whether it holds text or a picture.")
        self.source = theme.FilePicker(
            "Drop the file here", "or click to browse",
            "Choose the file with the secret", SOURCE_FILTER)
        self.source.fileChanged.connect(self._on_source_changed)
        self.step1.body.addWidget(self.source)
        return self.step1

    # -- step 2 --------------------------------------------------------

    def _key_step(self):
        self.step2 = theme.StepCard(
            2, "Enter the password",
            "The same password that was used to hide the secret.")
        self.key = theme.PasswordField("Password")
        self.key.edit.returnPressed.connect(self._start_extract)
        self.key.edit.textChanged.connect(lambda t: self.step2.set_done(bool(t)))
        self.step2.body.addWidget(self.key)
        return self.step2

    # -- result --------------------------------------------------------

    def _result_card(self):
        self.result_card = QtWidgets.QFrame()
        self.result_card.setObjectName("card")
        lay = QtWidgets.QVBoxLayout(self.result_card)
        lay.setContentsMargins(24, 20, 24, 22)
        lay.setSpacing(14)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(theme.icon_label("check", 22, theme.SUCCESS))
        self.result_title = theme.label("Hidden message", "stepTitle")
        head.addWidget(self.result_title)
        head.addStretch()
        lay.addLayout(head)

        self.legacy_note = theme.label(
            "This file was made by an older Whisper version that used weak "
            "protection. Hide the secret again with this version to keep it safe.",
            "hint", wrap=True)
        lay.addWidget(self.legacy_note)

        self.result_stack = QtWidgets.QStackedWidget()
        self.result_text = QtWidgets.QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(140)
        self.result_stack.addWidget(self.result_text)
        self.result_image = QtWidgets.QLabel()
        self.result_image.setAlignment(QtCore.Qt.AlignCenter)
        self.result_image.setMinimumHeight(160)
        self.result_image.setStyleSheet(
            "background: %s; border: 1px solid %s; border-radius: 10px; padding: 8px;"
            % (theme.SURFACE_ALT, theme.BORDER))
        self.result_stack.addWidget(self.result_image)
        lay.addWidget(self.result_stack)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(8)
        self.copy_btn = QtWidgets.QPushButton("Copy text")
        self.copy_btn.clicked.connect(self._copy)
        buttons.addWidget(self.copy_btn)
        self.save_btn = QtWidgets.QPushButton("Save to file…")
        self.save_btn.clicked.connect(self._save)
        buttons.addWidget(self.save_btn)
        buttons.addStretch()
        lay.addLayout(buttons)

        self.result_card.hide()
        return self.result_card

    # -- helpers -------------------------------------------------------

    def _clear_result(self):
        self._image_bytes = None
        self._text = ""
        self.result_text.clear()
        self.result_image.clear()
        self.result_card.hide()
        self.banner.clear()

    def _on_source_changed(self, path):
        self._clear_result()
        self.step1.set_done(bool(path))
        if not path:
            return
        name = os.path.basename(path)
        size = theme.human_bytes(os.path.getsize(path)) if os.path.exists(path) else ""
        card = self.source.card
        kind = engine.carrier_kind(path)
        if kind == "image":
            card.set_file(name, "Picture · %s" % size, thumb_path=path)
            lossy = os.path.splitext(path)[1].lower() not in engine.LOSSLESS_IMAGE_EXTENSIONS
            card.set_badge("Whisper never saves JPEG/WebP — use the PNG it made" if lossy else "",
                           "warn")
        elif kind in ("wav", "mp3"):
            card.set_file(name, "%s audio · %s" % (kind.upper(), size), icon_name="music")
            card.set_badge("")
        else:
            card.set_file(name, size)
            card.set_badge("Not supported — choose a picture, WAV or MP3", "danger")

    # -- extract -------------------------------------------------------

    def _start_extract(self):
        if self._worker is not None and self._worker.isRunning():
            return
        path = self.source.path
        if not path or not os.path.exists(path):
            self.banner.show_message("warn", "Choose the file with the secret first (step 1).")
            return
        if engine.carrier_kind(path) is None:
            self.banner.show_message("warn", "That file type isn't supported. "
                                             "Choose a picture, WAV or MP3.")
            return
        if not self.key.text():
            self.banner.show_message("warn", "Enter the password (step 2).")
            return

        self._clear_result()
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("Unlocking…")
        self.banner.show_message("busy", "Unlocking %s…" % html.escape(os.path.basename(path)))

        self._worker = ExtractWorker(path, self.key.text())
        self._worker.recovered.connect(self._on_recovered)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("Unlock")
        self._worker = None

    def _on_recovered(self, result):
        self.legacy_note.setVisible(bool(result.legacy))
        if result.text is not None:
            self._text = result.text
            self.result_title.setText("Hidden message")
            self.result_stack.setCurrentWidget(self.result_text)
            self.result_text.setPlainText(result.text)
            self.copy_btn.show()
            self.banner.show_message("success", "Unlocked! The message is shown below.")
        else:
            try:
                pixmap, size, fmt = self._to_pixmap(result.image_bytes)
            except Exception:
                self.banner.show_message("error", "The hidden picture is damaged and "
                                                  "can't be shown.")
                return
            self._image_bytes = result.image_bytes
            self._image_format = fmt
            self.result_title.setText("Hidden picture · %d × %d" % size)
            self.result_stack.setCurrentWidget(self.result_image)
            self.result_image.setPixmap(pixmap)
            self.copy_btn.hide()
            self.banner.show_message("success", "Unlocked! The picture is shown below.")
        self.result_card.show()
        self.scroll_to(self.result_card)

    @staticmethod
    def _to_pixmap(data):
        """(preview QPixmap, (w, h), PIL format) for encoded picture bytes."""
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            fmt = image.format or "PNG"
            size = image.size
            rgb = image.convert("RGB")
        raw = rgb.tobytes("raw", "RGB")
        qimage = QtGui.QImage(raw, size[0], size[1], size[0] * 3, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimage.copy())
        if pixmap.width() > 640 or pixmap.height() > 360:
            pixmap = pixmap.scaled(640, 360, QtCore.Qt.KeepAspectRatio,
                                   QtCore.Qt.SmoothTransformation)
        return pixmap, size, fmt

    def _on_failed(self, message):
        self.banner.show_message("error", html.escape(message))

    # -- results -------------------------------------------------------

    def _save(self):
        if self._image_bytes is not None:
            ext, flt = _IMAGE_SAVE.get(self._image_format, (".png", "PNG picture (*.png)"))
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.window(), "Save the hidden picture", "hidden_picture" + ext,
                flt + ";;All files (*)")
            if not path:
                return
            if not os.path.splitext(path)[1]:
                path += ext
            data, mode = self._image_bytes, "wb"
        elif self._text:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.window(), "Save the hidden message", "hidden_message.txt",
                "Text files (*.txt);;All files (*)")
            if not path:
                return
            data, mode = self._text, "w"
        else:
            return
        try:
            if mode == "wb":
                with open(path, "wb") as handle:
                    handle.write(data)
            else:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(data)
        except OSError as exc:
            self.banner.show_message("error", "Couldn't save: %s"
                                     % html.escape(exc.strerror or str(exc)))
            return
        self.banner.show_message("success", "Saved as <b>%s</b>."
                                 % html.escape(os.path.basename(path)))

    def _copy(self):
        if self._text:
            QtWidgets.QApplication.clipboard().setText(self._text)
            self.banner.show_message("success", "Copied to the clipboard.")


def main():
    app = QtWidgets.QApplication(sys.argv)
    theme.apply(app)
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Whisper — Read a hidden message")
    window.resize(880, 760)
    window.setCentralWidget(RevealPage())
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
