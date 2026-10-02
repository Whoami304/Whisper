"""Read-only support for files written by Whisper v1.

Whisper v1 appended a plain trailer to every file it wrote:

    <carrier bytes> \\n--PASS--\\n <sha256(password) hex> \\n--ALGO--\\n <aes|reverse|caser>

and hid the payload with sequential LSB (text: the "stegano" layout
"<byte count>:<data>"; pictures: a 64-bit width/height header followed by
raw RGB pixels) or in an ID3 comment (MP3). Pictures were never encrypted.

That design is not safe (see SECURITY.md), so v2 never writes it. This
module only lets people open what they already made. It needs neither
stegano nor pycryptodome.
"""

import base64
import hashlib
import hmac
import io
import os
import string

import numpy as np
from PIL import Image

from engine import Revealed, WhisperError

PASS_MARKER = b"\n--PASS--\n"
ALGO_MARKER = b"\n--ALGO--\n"
_TRAILER_SCAN = 512          # the trailer is short; only the file's tail is read


def _read_trailer(path: str):
    """(password_hash_hex, algo) or None if the file has no v1 trailer."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - _TRAILER_SCAN))
            tail = f.read()
    except OSError:
        return None
    if ALGO_MARKER not in tail:
        return None
    head, algo = tail.rsplit(ALGO_MARKER, 1)
    if PASS_MARKER not in head:
        return None
    pw_hash = head.rsplit(PASS_MARKER, 1)[1]
    try:
        return pw_hash.decode("ascii"), algo.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_legacy_file(path: str) -> bool:
    return _read_trailer(path) is not None


def reveal_legacy(path: str, password: str) -> Revealed:
    trailer = _read_trailer(path)
    if trailer is None:
        raise WhisperError("Wrong password, or this file has no Whisper secret in it.")
    pw_hash, algo = trailer
    expected = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(expected, pw_hash):
        raise WhisperError("Wrong password, or this file has no Whisper secret in it.")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3":
        return Revealed(text=_decrypt(algo, _mp3_comment(path), password), legacy=True)

    pixels = np.array(Image.open(path).convert("RGB"), dtype=np.uint8)
    lsbs = pixels.reshape(-1) & 1
    text = _stegano_text(lsbs)
    if text is not None:
        try:
            return Revealed(text=_decrypt(algo, text, password), legacy=True)
        except WhisperError:
            pass
    image = _legacy_image(lsbs)
    if image is not None:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return Revealed(image_bytes=buf.getvalue(), legacy=True)
    raise WhisperError("This old Whisper file is damaged and can't be read.")


# --- v1 payload layouts -----------------------------------------------------------------

def _stegano_text(lsbs: np.ndarray):
    """The "stegano" layout: bytes MSB-first, '<n>:' then n bytes of UTF-8."""
    head = np.packbits(lsbs[:8 * 24]).tobytes()
    colon = head.find(b":")
    if colon <= 0 or not head[:colon].isdigit():
        return None
    n = int(head[:colon])
    start = colon + 1
    if n <= 0 or (start + n) * 8 > lsbs.size:
        return None
    data = np.packbits(lsbs[: (start + n) * 8]).tobytes()[start:]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _legacy_image(lsbs: np.ndarray):
    """v1 picture: 32-bit width, 32-bit height, then 24 bits per pixel."""
    if lsbs.size < 64:
        return None
    w = int("".join(map(str, lsbs[:32])), 2)
    h = int("".join(map(str, lsbs[32:64])), 2)
    if not (0 < w < 20000 and 0 < h < 20000) or 64 + w * h * 24 > lsbs.size:
        return None
    raw = np.packbits(lsbs[64:64 + w * h * 24]).reshape(h, w, 3)
    return Image.fromarray(raw, "RGB")


def _mp3_comment(path: str) -> str:
    from mutagen.id3 import ID3
    try:
        frames = ID3(path).getall("COMM:hidden_steg_text:eng")
    except Exception:
        frames = []
    if not frames or not frames[0].text:
        raise WhisperError("This old Whisper file is damaged and can't be read.")
    return str(frames[0].text[0]).strip()


# --- v1 "ciphers" ---------------------------------------------------------------------------

_CAESAR_ALPHABET = string.printable
_SHIFTS = [i for i in range(2, 17) if i % 2 == 0]


def _decrypt(algo: str, data: str, password: str) -> str:
    try:
        if algo == "aes":
            from cryptography.hazmat.primitives import padding
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            raw = base64.b64decode("".join(c for c in data if not c.isspace()), validate=True)
            if len(raw) < 32 or len(raw) % 16:
                raise ValueError("bad length")
            key = hashlib.sha256(password.encode("utf-8")).digest()
            dec = Cipher(algorithms.AES(key), modes.CBC(raw[:16])).decryptor()
            padded = dec.update(raw[16:]) + dec.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
        if algo == "reverse":
            return bytes.fromhex(data)[::-1].decode("utf-8")
        if algo == "caser":
            shift = _SHIFTS[hashlib.sha256(password.encode("utf-8")).digest()[0] % len(_SHIFTS)]
            n = len(_CAESAR_ALPHABET)
            return "".join(_CAESAR_ALPHABET[(_CAESAR_ALPHABET.find(c) - shift) % n]
                           if c in _CAESAR_ALPHABET else c for c in data)
    except Exception:
        raise WhisperError("This old Whisper file is damaged and can't be read.")
    raise WhisperError("This old Whisper file uses an unknown method (%s)." % algo)
