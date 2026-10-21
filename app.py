"""Start the Whisper desktop app:  python app.py

    python app.py --selftest [REPORT]
        Run a quick end-to-end check without user interaction (used to verify
        the packaged Whisper.exe): hide and reveal text and a picture in a PNG,
        a WAV and an MP3, check that a wrong password is refused, then open
        every screen and switch the theme. Writes a report to REPORT (default:
        whisper-selftest.txt next to the program) and exits with 0 on success.
"""

import sys


def _selftest(report_path=None):
    import os
    import tempfile
    import traceback
    import wave

    base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                           else __file__))
    report_path = report_path or os.path.join(base, "whisper-selftest.txt")
    lines, ok = [], True

    def step(name, fn):
        nonlocal ok
        try:
            detail = fn()
            lines.append("PASS  %s%s" % (name, "  (%s)" % detail if detail else ""))
        except Exception:
            ok = False
            lines.append("FAIL  %s\n%s" % (name, traceback.format_exc()))

    tmp = tempfile.mkdtemp(prefix="whisper-selftest-")
    try:
        import gui  # noqa: F401  (sets sys.path for the engine)
        import numpy as np
        from PIL import Image
        import engine

        rng = np.random.default_rng(7)
        png = os.path.join(tmp, "carrier.png")
        Image.fromarray(rng.integers(0, 256, (200, 260, 3), dtype=np.uint8)).save(png)
        wav = os.path.join(tmp, "carrier.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes((rng.integers(-8000, 8000, 22050 * 2)).astype("<i2").tobytes())
        mp3 = os.path.join(tmp, "carrier.mp3")
        with open(mp3, "wb") as f:
            f.write((b"\xff\xfb\x90\x64" + b"\x00" * 413) * 20)
        secret = os.path.join(tmp, "secret.png")
        Image.fromarray(rng.integers(0, 256, (24, 32, 3), dtype=np.uint8)).save(secret)
        pw, msg = "selftest-Pass-123!", "Привет, Whisper! ✓ selftest"

        def text_roundtrip(carrier):
            def run():
                out = os.path.join(tmp, "out_" + os.path.basename(carrier))
                out = os.path.splitext(out)[0] + engine.output_extension(carrier)
                engine.hide_text(carrier, out, msg, pw)
                got = engine.reveal(out, pw).text
                assert got == msg, "got %r" % got
                return os.path.basename(out)
            return run

        for c in (png, wav, mp3):
            step("hide/reveal text in %s" % os.path.splitext(c)[1], text_roundtrip(c))

        def image_roundtrip():
            out = os.path.join(tmp, "out_img.png")
            engine.hide_image(png, out, secret, pw)
            res = engine.reveal(out, pw)
            assert res.image_bytes, "no picture recovered"
            return "%d bytes" % len(res.image_bytes)
        step("hide/reveal picture in .png", image_roundtrip)

        def wrong_password():
            out = os.path.join(tmp, "out_carrier.png")
            try:
                engine.reveal(out, "definitely-wrong")
            except engine.WhisperError:
                return "refused"
            raise AssertionError("wrong password was accepted")
        step("wrong password is refused", wrong_password)

        def gui_smoke():
            from PyQt5 import QtWidgets
            from gui import theme
            from gui.StartWindow.mainWindow import MainWindow
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
            theme.apply(app)
            win = MainWindow()
            win.show()
            app.processEvents()
            win.ui.openHideMessageWindow()
            page = win.ui.hide_page
            page.carrier.set_path(png)
            page.payload_edit.setPlainText(msg)
            app.processEvents()
            win.ui.goHome()
            win.ui.openRevealContentWindow()
            app.processEvents()
            start = theme.MODE
            theme.switch_theme(animate=False)
            theme.switch_theme(start, animate=False)
            assert page.payload_edit.toPlainText() == msg
            win.close()
            app.processEvents()
            return "Qt platform: %s" % app.platformName()
        step("open every screen and switch theme", gui_smoke)
    except Exception:
        ok = False
        lines.append("FAIL  setup\n" + traceback.format_exc())

    lines.insert(0, "Whisper self-test: %s" % ("OK" if ok else "FAILED"))
    text = "\n".join(lines) + "\n"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass
    try:
        print(text)
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(_selftest(sys.argv[2] if len(sys.argv) > 2 else None))
    from gui.StartWindow.mainWindow import main
    main()
