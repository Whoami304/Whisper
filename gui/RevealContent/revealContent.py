"""The Reveal window: recover a payload from a file that carries one.

Rewritten from the generated Qt Designer version, which had the same
converter layout as the Hide window and three specific problems beyond
its looks. Its Decode button was connected to two different handlers, so
one click ran both and each overwrote the other's result. It read the
file path from a label that only ever held the file's base name, so
decoding failed unless the app happened to be running in that directory.
And it ran the engine on the UI thread, so the window froze for the whole
operation.

The layout follows the order the work happens in:

    01 SOURCE -> 02 KEY -> 03 OPERATION -> 04 RECOVERED

A payload can be text or a hidden image, and which one it is cannot be
told from the file, so stage 01 asks. Getting it wrong is safe: the
window says the payload is not of that kind rather than showing rubbish.
"""

import os
import sys
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

import gui  # sets sys.path for both the GUI and the engine

from gui import theme
# Flat import, matching how the engine imports itself (see the note in
# the Hide window).
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
            # decode_with_password reports its reason on the console and
            # returns None; the window has to say something useful, and
            # the wrong key is by far the most common cause.
            self.failed.emit(
                "Nothing could be recovered. The key may be wrong, the file "
                "may hold no payload, or the payload may not be of the kind "
                "selected above.")
            return
        self.recovered.emit(result)


class Ui_MainWindow(object):
    """Kept as Ui_MainWindow with setupUi() so the start window's
    navigation keeps working unchanged."""

    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow
        self._worker = None
        self._ready = False
        self._recovered_image = None
        self._recovered_text = ""

        MainWindow.setObjectName("RevealWindow")
        MainWindow.setWindowTitle("Whisper - Reveal Content")
        MainWindow.resize(940, 720)
        MainWindow.setMinimumSize(720, 500)
        MainWindow.setAcceptDrops(True)
        MainWindow.dragEnterEvent = self._drag_enter
        MainWindow.dropEvent = self._drop

        page = theme.scrollable(MainWindow)
        head, self.chip = theme.masthead(
            "WHISPER  //  EXTRACT",
            "Recover what is hidden in a file",
            "Point at a file Whisper produced and give the key it was made "
            "with. Nothing is written to disk until you save it.")
        page.addLayout(head)
        page.addWidget(self._source_stage())
        page.addWidget(self._key_stage())
        page.addWidget(self._operation_stage())
        page.addWidget(self._result_stage())
        page.addStretch()

        self._ready = True
        self._on_source_changed()
        self._log("Ready. Choose a file to examine.")

    # -- stage 01 ------------------------------------------------------

    def _source_stage(self):
        frame, content = theme.module("01", "SOURCE")

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.source_input = QtWidgets.QLineEdit()
        self.source_input.setPlaceholderText(
            "Path to the file holding the payload, or drop one on this window")
        self.source_input.textChanged.connect(self._on_source_changed)
        row.addWidget(self.source_input, 1)
        browse = QtWidgets.QPushButton("BROWSE")
        browse.clicked.connect(self._browse_source)
        row.addWidget(browse)
        content.addLayout(row)

        meta = QtWidgets.QHBoxLayout()
        meta.setSpacing(26)
        kind_box, self.out_kind = theme.readout("TYPE")
        size_box, self.out_size = theme.readout("FILE SIZE")
        mark_box, self.out_mark = theme.readout("WHISPER PAYLOAD")
        for box in (kind_box, size_box, mark_box):
            meta.addLayout(box)
        meta.addStretch()
        content.addLayout(meta)

        content.addWidget(theme.micro_label("EXPECTED PAYLOAD"))
        switch = QtWidgets.QHBoxLayout()
        switch.setSpacing(6)
        self.mode_text = QtWidgets.QRadioButton("TEXT")
        self.mode_image = QtWidgets.QRadioButton("IMAGE FILE")
        self.mode_text.setChecked(True)
        group = QtWidgets.QButtonGroup(self.MainWindow)
        group.addButton(self.mode_text)
        group.addButton(self.mode_image)
        self._mode_group = group
        switch.addWidget(self.mode_text)
        switch.addWidget(self.mode_image)
        switch.addStretch()
        content.addLayout(switch)
        return frame

    # -- stage 02 ------------------------------------------------------

    def _key_stage(self):
        frame, content = theme.module("02", "KEY")

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.key_input.setPlaceholderText("The key this file was made with")
        self.key_input.returnPressed.connect(self._start_extract)
        row.addWidget(self.key_input, 1)
        self.reveal_btn = QtWidgets.QPushButton("SHOW")
        self.reveal_btn.setCheckable(True)
        self.reveal_btn.toggled.connect(self._toggle_key)
        row.addWidget(self.reveal_btn)
        content.addLayout(row)

        note = QtWidgets.QLabel(
            "The cipher is read from the file itself, so there is nothing "
            "else to match. A wrong key is refused outright rather than "
            "producing rubbish that looks like a payload.")
        note.setObjectName("note")
        note.setWordWrap(True)
        content.addWidget(note)
        return frame

    # -- stage 03 ------------------------------------------------------

    def _operation_stage(self):
        frame, content = theme.module("03", "OPERATION")

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)
        self.extract_btn = QtWidgets.QPushButton("EXTRACT PAYLOAD")
        self.extract_btn.setObjectName("primary")
        self.extract_btn.clicked.connect(self._start_extract)
        actions.addWidget(self.extract_btn)
        actions.addStretch()
        self.back_btn = QtWidgets.QPushButton("BACK")
        self.back_btn.setObjectName("ghost")
        self.back_btn.clicked.connect(self._go_back)
        actions.addWidget(self.back_btn)
        content.addLayout(actions)

        status_row = QtWidgets.QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(theme.micro_label("STATUS"))
        self.status_label = QtWidgets.QLabel("Nothing extracted yet.")
        self.status_label.setObjectName("note")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        content.addLayout(status_row)
        return frame

    # -- stage 04 ------------------------------------------------------

    def _result_stage(self):
        frame, content = theme.module("04", "RECOVERED")

        self.result_stack = QtWidgets.QStackedWidget()

        self.result_text = QtWidgets.QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText(
            "The recovered payload appears here.")
        self.result_text.setMinimumHeight(150)
        self.result_stack.addWidget(self.result_text)

        self.result_image = QtWidgets.QLabel("")
        self.result_image.setAlignment(QtCore.Qt.AlignCenter)
        self.result_image.setMinimumHeight(150)
        self.result_image.setStyleSheet(
            "background: %s; border: 1px solid %s;"
            % (theme.PANEL_DEEP, theme.RULE))
        self.result_stack.addWidget(self.result_image)
        content.addWidget(self.result_stack)

        save_row = QtWidgets.QHBoxLayout()
        save_row.setSpacing(8)
        self.save_btn = QtWidgets.QPushButton("SAVE PAYLOAD")
        self.save_btn.setObjectName("secondary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        save_row.addWidget(self.save_btn)
        self.copy_btn = QtWidgets.QPushButton("COPY TEXT")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy)
        save_row.addWidget(self.copy_btn)
        save_row.addStretch()
        content.addLayout(save_row)

        content.addWidget(theme.micro_label("OPERATION LOG"))
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(84)
        content.addWidget(self.log_view)
        return frame

    # -- helpers -------------------------------------------------------

    def _log(self, message):
        """One timestamped line. Never receives a key or a payload."""
        self.log_view.appendPlainText(
            "%s  %s" % (datetime.now().strftime("%H:%M:%S"), message))

    def _mode(self):
        return MODE_TEXT if self.mode_text.isChecked() else MODE_IMAGE

    def _toggle_key(self, shown):
        self.key_input.setEchoMode(
            QtWidgets.QLineEdit.Normal if shown else QtWidgets.QLineEdit.Password)
        self.reveal_btn.setText("HIDE" if shown else "SHOW")

    def _on_source_changed(self):
        if not self._ready:
            return
        path = self.source_input.text().strip().strip('"')
        if not path or not os.path.exists(path):
            self.out_kind.setText("--" if not path else "NOT FOUND")
            self.out_size.setText("--")
            self.out_mark.setText("--")
            return

        extension = os.path.splitext(path)[1].lower()
        self.out_kind.setText({".png": "PNG IMAGE",
                               ".mp3": "MP3 AUDIO"}.get(extension, "OTHER"))
        self.out_size.setText(theme.human_bytes(os.path.getsize(path)))

        # The trailer Whisper appends is the one reliable tell that a file
        # came from this app, and reading it needs no key.
        try:
            with open(path, "rb") as handle:
                blob = handle.read()
            self.out_mark.setText(
                "DETECTED" if b"\n--ALGO--\n" in blob else "NONE")
        except OSError:
            self.out_mark.setText("UNREADABLE")

    def _browse_source(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.MainWindow, "Select the file to examine", "",
            "Whisper output (*.png *.mp3);;PNG image (*.png);;"
            "MP3 audio (*.mp3);;All files (*)")
        if path:
            self.source_input.setText(os.path.abspath(path))

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile():
            self.source_input.setText(os.path.abspath(urls[0].toLocalFile()))

    # -- extract -------------------------------------------------------

    def _start_extract(self):
        path = self.source_input.text().strip().strip('"')
        if not path or not os.path.exists(path):
            theme.set_chip(self.chip, "BLOCKED", theme.CAUTION)
            self.status_label.setText("Choose a file to examine first.")
            return

        self.extract_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self._recovered_image = None
        self._recovered_text = ""
        self.result_text.clear()
        self.result_image.clear()
        theme.set_chip(self.chip, "EXTRACTING", theme.SIGNAL)
        self.status_label.setText("Extracting from %s..." % os.path.basename(path))
        self._log("EXTRACT  source=%s  expecting=%s"
                  % (os.path.basename(path), self._mode()))

        self._worker = ExtractWorker(path, self.key_input.text(), self._mode())
        self._worker.recovered.connect(self._on_recovered)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(lambda: self.extract_btn.setEnabled(True))
        self._worker.start()

    def _on_recovered(self, payload):
        theme.set_chip(self.chip, "RECOVERED", theme.OKAY)
        if isinstance(payload, str):
            self._recovered_text = payload
            self.result_stack.setCurrentWidget(self.result_text)
            self.result_text.setPlainText(payload)
            self.status_label.setText("Recovered %d characters." % len(payload))
            self._log("Recovered a text payload of %d characters." % len(payload))
            self.copy_btn.setEnabled(True)
        else:
            self._recovered_image = payload
            self.result_stack.setCurrentWidget(self.result_image)
            self.result_image.setPixmap(self._to_pixmap(payload))
            self.status_label.setText(
                "Recovered an image payload of %d x %d pixels." % payload.size)
            self._log("Recovered an image payload of %d x %d." % payload.size)
        self.save_btn.setEnabled(True)

    def _to_pixmap(self, image):
        """A PIL image as a QPixmap, scaled to the preview area."""
        rgb = image.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        qimage = QtGui.QImage(data, rgb.size[0], rgb.size[1],
                              rgb.size[0] * 3, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimage)
        box = self.result_image.size()
        if pixmap.width() > box.width() or pixmap.height() > box.height():
            pixmap = pixmap.scaled(box, QtCore.Qt.KeepAspectRatio,
                                   QtCore.Qt.SmoothTransformation)
        return pixmap

    def _on_failed(self, message):
        theme.set_chip(self.chip, "FAILED", theme.ALERT)
        self.status_label.setText(message)
        self.result_stack.setCurrentWidget(self.result_text)
        self._log("FAILED  extraction did not produce a payload.")

    # -- results -------------------------------------------------------

    def _save(self):
        if self._recovered_image is not None:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.MainWindow, "Save the recovered image",
                "recovered_payload.png", "PNG image (*.png);;All files (*)")
            if not path:
                return
            try:
                self._recovered_image.save(path)
            except Exception as exc:
                self.status_label.setText("Could not save: %s" % exc)
                return
            self.status_label.setText("Saved to %s" % path)
            self._log("Saved the recovered image.")
            return

        if not self._recovered_text:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.MainWindow, "Save the recovered text", "recovered_payload.txt",
            "Text files (*.txt);;All files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._recovered_text)
        except OSError as exc:
            self.status_label.setText("Could not save: %s" % exc)
            return
        self.status_label.setText("Saved to %s" % path)
        self._log("Saved the recovered text.")

    def _copy(self):
        if self._recovered_text:
            QtWidgets.QApplication.clipboard().setText(self._recovered_text)
            self.status_label.setText("Copied to the clipboard.")

    def _go_back(self):
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
