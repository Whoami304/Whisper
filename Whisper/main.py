"""Whisper command line.

    python -m Whisper.main hide-text  CARRIER OUTPUT  (-m TEXT | -f FILE)
    python -m Whisper.main hide-image CARRIER OUTPUT  SECRET_PICTURE
    python -m Whisper.main reveal     FILE  [-o OUT]
    python -m Whisper.main capacity   CARRIER

The password is asked for interactively (never echoed, never put on the
command line where it would land in shell history). For scripting, set
WHISPER_PASSWORD instead.
"""

import argparse
import getpass
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine  # noqa: E402


def _password(confirm: bool) -> str:
    env = os.environ.get("WHISPER_PASSWORD")
    if env:
        return env
    pw = getpass.getpass("Password: ")
    if not pw:
        raise engine.WhisperError("A password is required.")
    if confirm:
        if getpass.getpass("Repeat password: ") != pw:
            raise engine.WhisperError("The passwords don't match.")
        score, word = engine.password_strength(pw)
        if score <= 1:
            print("Warning: this password is %s." % word.lower(), file=sys.stderr)
    return pw


def cmd_hide_text(args) -> int:
    if (args.message is None) == (args.file is None):
        raise engine.WhisperError("Give exactly one of -m TEXT or -f FILE.")
    if args.file is not None:
        with open(args.file, "r", encoding="utf-8") as fh:
            message = fh.read()
    else:
        message = args.message
    out = engine.hide_text(args.carrier, args.output, message, _password(True))
    print("Saved: %s" % out)
    return 0


def cmd_hide_image(args) -> int:
    out = engine.hide_image(args.carrier, args.output, args.secret, _password(True))
    print("Saved: %s" % out)
    return 0


def cmd_reveal(args) -> int:
    result = engine.reveal(args.file, _password(False))
    if result.legacy:
        print("Note: this file was made by an old Whisper version with weak "
              "protection. Re-hide the secret with this version.", file=sys.stderr)
    if result.text is not None:
        if args.output:
            with open(args.output, "w", encoding="utf-8", newline="") as fh:
                fh.write(result.text)
            print("Saved: %s" % args.output)
        else:
            print(result.text)
        return 0
    output = args.output
    if not output:
        from PIL import Image
        with Image.open(io.BytesIO(result.image_bytes)) as im:
            ext = {"JPEG": ".jpg"}.get(im.format, "." + (im.format or "png").lower())
        output = "hidden_picture" + ext
    if os.path.exists(output) and not args.force:
        raise engine.WhisperError("%s already exists (use --force to overwrite)." % output)
    with open(output, "wb") as fh:
        fh.write(result.image_bytes)
    print("Hidden picture saved: %s" % output)
    return 0


def cmd_capacity(args) -> int:
    cap = engine.capacity(args.carrier)
    if cap is None:
        print("MP3: no fixed limit (stored in an ID3 tag).")
    else:
        print("%s (%d bytes)" % (engine.human_bytes(cap), cap))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="whisper", description="Hide encrypted secrets in "
                                "pictures and audio files.")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("hide-text", help="hide a text message")
    t.add_argument("carrier")
    t.add_argument("output")
    t.add_argument("-m", "--message")
    t.add_argument("-f", "--file", help="read the message from a UTF-8 text file")
    t.set_defaults(func=cmd_hide_text)

    i = sub.add_parser("hide-image", help="hide a picture")
    i.add_argument("carrier")
    i.add_argument("output")
    i.add_argument("secret", help="the picture to hide")
    i.set_defaults(func=cmd_hide_image)

    r = sub.add_parser("reveal", help="read a hidden secret")
    r.add_argument("file")
    r.add_argument("-o", "--output", help="save the secret to this file")
    r.add_argument("--force", action="store_true", help="overwrite an existing output")
    r.set_defaults(func=cmd_reveal)

    c = sub.add_parser("capacity", help="how much a carrier can hold")
    c.add_argument("carrier")
    c.set_defaults(func=cmd_capacity)
    return p


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except engine.WhisperError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    except OSError as exc:
        print("Error: %s" % (exc.strerror or exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
