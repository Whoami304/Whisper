"""The Reveal page: read a secret hidden in a file made by Whisper.

Choose the file, say what kind of secret to expect, enter the password,
and press Unlock. Whether the file carries a Whisper secret at all can be
told without the password (Whisper appends a small marker), so the file
card says so straight away.

Engine calls are unchanged from the previous version. Extraction runs on
a QThread so the window never freezes.
"""

import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import gui  # sets sys.path for both the GUI and the engine

from gui import theme
from StegoTextPass import StegoTextPass

MODE_TEXT = "text"
MODE_IMAGE = "image"


class ExtractWorker(QtCore.QThread):
    """Runs one extraction off the UI thread."""

    recovered = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, path, password, data_type, parent=None):
        super(ExtractWorker, self).__init__(parent)
        self.path = path
        self.password = password
        self.data_type = data_type

    def run(self):
        try:
            result = StegoTextPass().decode_with_password(
                self.path, self.password, self.data_type)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if result is None:
            self.failed.emit(
                "Couldn't unlock this file. Check the password, and that "
                "“What's hidden” matches what was put in.")
            return
        self.recovered.emit(result)


class RevealPage(theme.Page):

    def __init__(self, on_back=None, parent=None):
        super(RevealPage, self).__init__("Read a hidden message", on_back, parent)
        self._worker = None
        self._recovered_image = None
        self._recovered_text = ""

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
            "A PNG picture or MP3 song that was saved with Whisper.")
        self.source = theme.FilePicker(
            "Drop the file here", "or click to browse",
            "Choose the file with the secret",
            "Pictures and songs (*.png *.mp3);;PNG picture (*.png);;"
            "MP3 song (*.mp3);;All files (*)")
        self.source.fileChanged.connect(self._on_source_changed)
        self.step1.body.addWidget(self.source)

        self.mode = theme.Segmented([("Text message", "text"), ("Picture", "image")])
        self.mode.changed.connect(lambda *_: self._clear_result())
        self.mode_hint = theme.label(
            "Pick what was hidden in this file.", "hint", wrap=True)
        self.step1.body.addLayout(theme.field("What's hidden?", self.mode, self.mode_hint))
        return self.step1

    # -- step 2 --------------------------------------------------------

    def _key_step(self):
        self.step2 = theme.StepCard(
            2, "Enter the password",
            "The same password that was used to hide the message.")
        self.key = theme.PasswordField("Password")
        self.key.edit.returnPressed.connect(self._start_extract)
        self.key.edit.textChanged.connect(
            lambda t: self.step2.set_done(bool(t)))
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

    def _mode(self):
        return MODE_TEXT if self.mode.index() == 0 else MODE_IMAGE

    def _clear_result(self):
        self.result_card.hide()
        self.banner.clear()

    def _on_source_changed(self, path):
        self._clear_result()
        self.step1.set_done(bool(path))
        picture_btn = self.mode.buttons[1]
        picture_btn.setEnabled(True)
        self.mode_hint.setText("Pick what was hidden in this file.")
        if not path:
            return

        name = os.path.basename(path)
        extension = os.path.splitext(path)[1].lower()
        size = theme.human_bytes(os.path.getsize(path)) if os.path.exists(path) else ""
        card = self.source.card
        if extension == ".png":
            card.set_file(name, "PNG picture · %s" % size, thumb_path=path)
        elif extension == ".mp3":
            card.set_file(name, "MP3 song · %s" % size, icon_name="music")
            self.mode.set_index(0)
            picture_btn.setEnabled(False)
            self.mode_hint.setText("Songs can only hold text messages.")
        else:
            card.set_file(name, size)

        # Whisper appends a marker that can be read without the password.
        try:
            with open(path, "rb") as handle:
                blob = handle.read()
            if b"\n--ALGO--\n" in blob:
                card.set_badge("Contains a Whisper secret", "success")
            else:
                card.set_badge("No Whisper secret found", "neutral")
        except OSError:
            card.set_badge("Can't read this file", "danger")

    # -- extract -------------------------------------------------------

    def _start_extract(self):
        if self._worker is not None and self._worker.isRunning():
            return
        path = self.source.path
        if not path or not os.path.exists(path):
            self.banner.show_message("warn", "Choose the file with the secret first (step 1).")
            return

        self._recovered_image = None
        self._recovered_text = ""
        self.result_card.hide()
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("Unlocking…")
        self.banner.show_message("busy", "Unlocking %s…" % os.path.basename(path))

        # MP3 files use the audio decode path; the UI mode alone can't say that.
        extension = os.path.splitext(path)[1].lower()
        mode = self._mode()
        data_type = "audio" if (extension == ".mp3" and mode == MODE_TEXT) else mode

        self._worker = ExtractWorker(path, self.key.text(), data_type)
        self._worker.recovered.connect(self._on_recovered)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("Unlock")
        self._worker = None

    def _on_recovered(self, payload):
        if isinstance(payload, str):
            self._recovered_text = payload
            self.result_title.setText("Hidden message")
            self.result_stack.setCurrentWidget(self.result_text)
            self.result_text.setPlainText(payload)
            self.copy_btn.show()
            self.banner.show_message("success", "Unlocked! The message is shown below.")
        else:
            self._recovered_image = payload
            self.result_title.setText("Hidden picture · %d × %d" % payload.size)
            self.result_stack.setCurrentWidget(self.result_image)
            self.result_image.setPixmap(self._to_pixmap(payload))
            self.copy_btn.hide()
            self.banner.show_message("success", "Unlocked! The picture is shown below.")
        self.result_card.show()
        self.scroll_to(self.result_card)

    def _to_pixmap(self, image):
        """A PIL image as a QPixmap, capped to a fixed preview size."""
        rgb = image.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        qimage = QtGui.QImage(data, rgb.size[0], rgb.size[1],
                              rgb.size[0] * 3, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimage.copy())
        max_w, max_h = 640, 360
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, QtCore.Qt.KeepAspectRatio,
                                   QtCore.Qt.SmoothTransformation)
        return pixmap

    def _on_failed(self, message):
        self.banner.show_message("error", message)

    # -- results -------------------------------------------------------

    def _save(self):
        if self._recovered_image is not None:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.window(), "Save the hidden picture",
                "hidden_picture.png", "PNG picture (*.png);;All files (*)")
            if not path:
                return
            try:
                self._recovered_image.save(path)
            except Exception as exc:
                self.banner.show_message("error", "Couldn't save: %s" % exc)
                return
        elif self._recovered_text:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.window(), "Save the hidden message", "hidden_message.txt",
                "Text files (*.txt);;All files (*)")
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(self._recovered_text)
            except OSError as exc:
                self.banner.show_message("error", "Couldn't save: %s" % exc)
                return
        else:
            return
        self.banner.show_message("success", "Saved as <b>%s</b>." % os.path.basename(path))

    def _copy(self):
        if self._recovered_text:
            QtWidgets.QApplication.clipboard().setText(self._recovered_text)
            self.banner.show_message("success", "Copied to the clipboard.")


class Ui_MainWindow(object):
    """Lets the page run on its own in a QMainWindow."""

    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        MainWindow.setWindowTitle("Whisper — Read a hidden message")
        MainWindow.resize(880, 760)
        self.page = RevealPage()
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
