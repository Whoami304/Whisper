"""Whisper engine v2: hide encrypted text or pictures inside images and audio.

This is the only module the GUI and the CLI talk to. Everything that used
to live in the separate cipher/stego classes is replaced by one design:

    password --scrypt(salt)--> 52 bytes --+--> AES-256-GCM key (32 B)
                                          +--> scatter key    (16 B)
                                          +--> length mask    ( 4 B)

    payload  = kind (1 B) || data
    sealed   = AES-256-GCM(key, nonce, payload, aad=b"WHISPER-v2")
    record   = (len(sealed)+12) XOR mask (4 B) || nonce (12 B) || sealed

Carriers
--------
PNG / BMP (any lossless image)
    The 16-byte salt goes into the least-significant bits of the first 128
    colour values. The record goes into the LSBs of colour values chosen
    by a keyed permutation of the rest of the image, so without the
    password nobody can even tell where (or whether) anything is written.
    Output is always PNG -- a lossy format would destroy the bits.
WAV (16-bit or 8-bit PCM)
    Same scheme over the audio samples.
MP3
    MP3 frames are re-quantised by every encoder, so LSB hiding is not
    possible. The sealed container is stored in an ID3 tag instead. It is
    encrypted and authenticated exactly like the others, but a tag editor
    will show that the tag exists. The GUI says so.

Security properties
-------------------
* Without the password the content cannot be read, and the file carries
  no marker, hash or length that would reveal anything was hidden (PNG/WAV).
* A wrong password and "nothing is hidden here" are indistinguishable:
  both fail the GCM authentication. Tampering fails the same check.
* Each guess costs one scrypt (N=2^15, r=8, p=1: ~100 ms and 32 MB), so
  offline guessing is slow. Weak passwords are still weak -- the GUI
  offers a generator.
* Hidden pictures are encrypted too (they were not, in v1).

Files written by Whisper v1 can still be read (see legacy.py).
"""

import base64
import hashlib
import io
import os
import secrets
import string
import wave
from dataclasses import dataclass
from typing import Optional

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image

FORMAT_AAD = b"WHISPER-v2"
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
LEN_FIELD = 4
KIND_TEXT = 1
KIND_IMAGE = 2
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 15, 8, 1

# Bytes a record adds around the data: length field, nonce, GCM tag, kind byte.
OVERHEAD = LEN_FIELD + NONCE_LEN + TAG_LEN + 1
SALT_BITS = SALT_LEN * 8

IMAGE_EXTENSIONS = (".png", ".bmp", ".tif", ".tiff", ".jpg", ".jpeg", ".webp")
LOSSLESS_IMAGE_EXTENSIONS = (".png", ".bmp", ".tif", ".tiff")
WAV_EXTENSIONS = (".wav",)
MP3_EXTENSIONS = (".mp3",)
CARRIER_EXTENSIONS = IMAGE_EXTENSIONS + WAV_EXTENSIONS + MP3_EXTENSIONS

ID3_DESC = "whisper"
MAX_SECRET_IMAGE_SIDE = 4096


class WhisperError(Exception):
    """A user-facing failure. The message is safe to show as it is."""


class WrongPasswordOrEmpty(WhisperError):
    """Authentication failed: wrong password, nothing hidden, or the file was altered."""

    def __init__(self):
        super().__init__("Wrong password, or this file has no Whisper secret in it.")


@dataclass
class Revealed:
    """What reveal() found. Exactly one of text / image_bytes is set."""
    text: Optional[str] = None
    image_bytes: Optional[bytes] = None
    legacy: bool = False

    @property
    def kind(self) -> str:
        return "text" if self.text is not None else "image"

    def image(self) -> Image.Image:
        return Image.open(io.BytesIO(self.image_bytes))


# --- key material ------------------------------------------------------------------

@dataclass(frozen=True)
class _Keys:
    aead: bytes
    scatter: bytes
    length_mask: int


def _derive(password: str, salt: bytes) -> _Keys:
    if not isinstance(password, str) or password == "":
        raise WhisperError("Enter a password.")
    out = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R,
                         p=SCRYPT_P, maxmem=64 * 1024 * 1024, dklen=52)
    return _Keys(out[:32], out[32:48], int.from_bytes(out[48:52], "big"))


def _seal(keys: _Keys, kind: int, data: bytes) -> bytes:
    nonce = secrets.token_bytes(NONCE_LEN)
    sealed = AESGCM(keys.aead).encrypt(nonce, bytes([kind]) + data, FORMAT_AAD)
    body = nonce + sealed
    return ((len(body) ^ keys.length_mask) & 0xFFFFFFFF).to_bytes(4, "big") + body


def _open(keys: _Keys, body: bytes) -> Revealed:
    try:
        plain = AESGCM(keys.aead).decrypt(body[:NONCE_LEN], body[NONCE_LEN:], FORMAT_AAD)
    except InvalidTag:
        raise WrongPasswordOrEmpty()
    kind, data = plain[0], plain[1:]
    if kind == KIND_TEXT:
        try:
            return Revealed(text=data.decode("utf-8"))
        except UnicodeDecodeError:
            raise WhisperError("The hidden text is damaged.")
    if kind == KIND_IMAGE:
        return Revealed(image_bytes=data)
    raise WhisperError("This file was made by a newer version of Whisper.")


# --- keyed scatter: a permutation of [0, m) -----------------------------------------

def _mix(x: np.ndarray) -> np.ndarray:
    """splitmix64 finaliser, vectorised (uint64 arithmetic wraps)."""
    x = x ^ (x >> np.uint64(30))
    x = x * np.uint64(0xBF58476D1CE4E5B9)
    x = x ^ (x >> np.uint64(27))
    x = x * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


class _Scatter:
    """Maps record bit i to a slot index in [0, m), a bijection keyed by the
    password. A 6-round Feistel network over the smallest even bit-width that
    covers m, made exact on [0, m) by cycle-walking."""

    ROUNDS = 6

    def __init__(self, key: bytes, m: int):
        if m <= 0:
            raise WhisperError("This file is too small to hide anything in.")
        self.m = m
        bits = max(2, (m - 1).bit_length())
        bits += bits % 2
        self.half = bits // 2
        self.half_mask = np.uint64((1 << self.half) - 1)
        seed = int.from_bytes(hashlib.sha256(b"whisper-scatter" + key).digest(), "big")
        words = [(seed >> (64 * j)) & 0xFFFFFFFFFFFFFFFF for j in range(4)]
        golden = 0x9E3779B97F4A7C15
        self.round_keys = [np.uint64(words[i % 4] ^ ((i * golden) & 0xFFFFFFFFFFFFFFFF))
                           for i in range(self.ROUNDS)]

    def _feistel(self, x: np.ndarray) -> np.ndarray:
        left = x >> np.uint64(self.half)
        right = x & self.half_mask
        for k in self.round_keys:
            left, right = right, left ^ (_mix(right ^ k) & self.half_mask)
        return (left << np.uint64(self.half)) | right

    def positions(self, start: int, count: int) -> np.ndarray:
        out = self._feistel(np.arange(start, start + count, dtype=np.uint64))
        bad = out >= np.uint64(self.m)
        while bad.any():
            out[bad] = self._feistel(out[bad])
            bad = out >= np.uint64(self.m)
        return out.astype(np.int64)


# --- bit helpers ----------------------------------------------------------------------

def _bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8)).tobytes()


_CHUNK = 1 << 22          # bits handled per pass (bounds memory on big files)


class _LsbCarrier:
    """A flat array of integer samples whose least-significant bits carry data."""

    def __init__(self, slots: np.ndarray):
        self.slots = slots                     # 1-D, any unsigned/signed int dtype

    @property
    def size(self) -> int:
        return int(self.slots.size)

    def capacity_bytes(self) -> int:
        """Largest `data` (after the kind byte) that fits."""
        return max(0, (self.size - SALT_BITS) // 8 - OVERHEAD)

    def write(self, password: str, kind: int, data: bytes) -> None:
        if self.size < SALT_BITS + 8 * (OVERHEAD + 1):
            raise WhisperError("This file is too small to hide anything in.")
        if len(data) > self.capacity_bytes():
            raise WhisperError(
                "Too big for this file: needs %s, the file can hold %s."
                % (human_bytes(len(data)), human_bytes(self.capacity_bytes())))
        salt = secrets.token_bytes(SALT_LEN)
        keys = _derive(password, salt)
        record = _seal(keys, kind, data)
        self._set(np.arange(SALT_BITS), _bits(salt))
        scatter = _Scatter(keys.scatter, self.size - SALT_BITS)
        bits = _bits(record)
        for start in range(0, bits.size, _CHUNK):
            chunk = bits[start:start + _CHUNK]
            self._set(scatter.positions(start, chunk.size) + SALT_BITS, chunk)

    def read(self, password: str) -> Revealed:
        if self.size < SALT_BITS + 8 * (OVERHEAD + 1):
            raise WrongPasswordOrEmpty()
        salt = _bytes(self._get(np.arange(SALT_BITS)))
        keys = _derive(password, salt)
        scatter = _Scatter(keys.scatter, self.size - SALT_BITS)
        head = _bytes(self._get(scatter.positions(0, LEN_FIELD * 8) + SALT_BITS))
        body_len = (int.from_bytes(head, "big") ^ keys.length_mask) & 0xFFFFFFFF
        max_body = (self.size - SALT_BITS) // 8 - LEN_FIELD
        if not (NONCE_LEN + TAG_LEN + 1 <= body_len <= max_body):
            raise WrongPasswordOrEmpty()
        parts = []
        first, total = LEN_FIELD * 8, body_len * 8
        for start in range(0, total, _CHUNK):
            count = min(_CHUNK, total - start)
            parts.append(self._get(scatter.positions(first + start, count) + SALT_BITS))
        return _open(keys, _bytes(np.concatenate(parts)))

    def _get(self, idx: np.ndarray) -> np.ndarray:
        return (self.slots[idx] & 1).astype(np.uint8)

    def _set(self, idx: np.ndarray, bits: np.ndarray) -> None:
        values = self.slots[idx]
        self.slots[idx] = (values & ~values.dtype.type(1)) | bits.astype(values.dtype)


# --- carriers: images -------------------------------------------------------------------

def _open_image_carrier(path: str):
    try:
        img = Image.open(path)
        img.load()
    except FileNotFoundError:
        raise WhisperError("File not found: %s" % path)
    except Exception as exc:
        raise WhisperError("This picture can't be opened (%s)." % exc)
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    mode = "RGBA" if has_alpha else "RGB"
    info = {"icc_profile": img.info.get("icc_profile")} if img.info.get("icc_profile") else {}
    arr = np.array(img.convert(mode), dtype=np.uint8)
    return arr, mode, info


def _image_slots(arr: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(arr[..., :3]).reshape(-1)


def image_capacity(path: str) -> int:
    """Bytes of hidden data a picture can hold (as the `data` part)."""
    arr, _, _ = _open_image_carrier(path)
    return _LsbCarrier(_image_slots(arr)).capacity_bytes()


def capacity_for_size(width: int, height: int) -> int:
    """Same as image_capacity() from dimensions alone (for the GUI meter)."""
    return max(0, (width * height * 3 - SALT_BITS) // 8 - OVERHEAD)


def _hide_in_image(carrier: str, output: str, password: str, kind: int, data: bytes) -> str:
    arr, mode, info = _open_image_carrier(carrier)
    slots = _image_slots(arr)
    lsb = _LsbCarrier(slots)
    lsb.write(password, kind, data)
    arr[..., :3] = slots.reshape(arr.shape[0], arr.shape[1], 3)
    _atomic_save(output, lambda f: Image.fromarray(arr, mode).save(f, format="PNG", **info))
    return output


def _reveal_from_image(path: str, password: str) -> Revealed:
    arr, _, _ = _open_image_carrier(path)
    return _LsbCarrier(_image_slots(arr)).read(password)


# --- carriers: WAV ------------------------------------------------------------------------

def _read_wav(path: str):
    try:
        with wave.open(path, "rb") as w:
            params = w.getparams()
            frames = w.readframes(params.nframes)
    except FileNotFoundError:
        raise WhisperError("File not found: %s" % path)
    except (wave.Error, EOFError) as exc:
        raise WhisperError("Only uncompressed PCM WAV files are supported (%s)." % exc)
    if params.sampwidth == 2:
        samples = np.frombuffer(frames, dtype="<i2").copy()
    elif params.sampwidth == 1:
        samples = np.frombuffer(frames, dtype=np.uint8).copy()
    else:
        raise WhisperError("Only 8-bit and 16-bit WAV files are supported.")
    return params, samples


def wav_capacity(path: str) -> int:
    _, samples = _read_wav(path)
    return _LsbCarrier(samples).capacity_bytes()


def _hide_in_wav(carrier: str, output: str, password: str, kind: int, data: bytes) -> str:
    params, samples = _read_wav(carrier)
    _LsbCarrier(samples).write(password, kind, data)

    def write(f):
        with wave.open(f, "wb") as w:
            w.setparams(params)
            w.writeframes(samples.tobytes())
    _atomic_save(output, write)
    return output


def _reveal_from_wav(path: str, password: str) -> Revealed:
    _, samples = _read_wav(path)
    return _LsbCarrier(samples).read(password)


# --- carriers: MP3 (ID3 tag) ---------------------------------------------------------------

def _hide_in_mp3(carrier: str, output: str, password: str, kind: int, data: bytes) -> str:
    from mutagen.id3 import ID3, ID3NoHeaderError, TXXX
    if not os.path.exists(carrier):
        raise WhisperError("File not found: %s" % carrier)
    salt = secrets.token_bytes(SALT_LEN)
    record = salt + _seal(_derive(password, salt), kind, data)
    tmp = _tmp_path(output)
    try:
        with open(carrier, "rb") as src, open(tmp, "wb") as dst:
            dst.write(src.read())
        try:
            tags = ID3(tmp)
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall("TXXX:" + ID3_DESC)
        tags.add(TXXX(encoding=3, desc=ID3_DESC, text=base64.b64encode(record).decode("ascii")))
        tags.save(tmp, v1=0, v2_version=3)
        os.replace(tmp, output)
    except WhisperError:
        raise
    except Exception as exc:
        raise WhisperError("Couldn't write the MP3 file (%s)." % exc)
    finally:
        _remove_quietly(tmp)
    return output


def _reveal_from_mp3(path: str, password: str) -> Revealed:
    from mutagen.id3 import ID3, ID3NoHeaderError
    try:
        frames = ID3(path).getall("TXXX:" + ID3_DESC)
    except ID3NoHeaderError:
        raise WrongPasswordOrEmpty()
    except FileNotFoundError:
        raise WhisperError("File not found: %s" % path)
    except Exception as exc:
        raise WhisperError("This MP3 can't be read (%s)." % exc)
    if not frames:
        raise WrongPasswordOrEmpty()
    try:
        record = base64.b64decode(frames[0].text[0], validate=True)
    except Exception:
        raise WrongPasswordOrEmpty()
    if len(record) < SALT_LEN + LEN_FIELD + NONCE_LEN + TAG_LEN + 1:
        raise WrongPasswordOrEmpty()
    salt, rest = record[:SALT_LEN], record[SALT_LEN:]
    keys = _derive(password, salt)
    body_len = (int.from_bytes(rest[:4], "big") ^ keys.length_mask) & 0xFFFFFFFF
    if body_len != len(rest) - 4:
        raise WrongPasswordOrEmpty()
    return _open(keys, rest[4:])


# --- public API ------------------------------------------------------------------------------

def carrier_kind(path: str) -> Optional[str]:
    """'image', 'wav', 'mp3', or None for an unsupported file."""
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in WAV_EXTENSIONS:
        return "wav"
    if ext in MP3_EXTENSIONS:
        return "mp3"
    return None


def output_extension(carrier: str) -> str:
    """The extension the result is saved with: images always become PNG."""
    kind = carrier_kind(carrier)
    return {"image": ".png", "wav": ".wav", "mp3": ".mp3"}.get(kind, "")


def capacity(path: str) -> Optional[int]:
    """Bytes of data a carrier can hold; None means "no practical limit" (MP3)."""
    kind = carrier_kind(path)
    if kind == "image":
        return image_capacity(path)
    if kind == "wav":
        return wav_capacity(path)
    if kind == "mp3":
        return None
    raise WhisperError("Unsupported file type. Use a picture (PNG, BMP, JPG), a WAV or an MP3.")


_HIDERS = {"image": _hide_in_image, "wav": _hide_in_wav, "mp3": _hide_in_mp3}
_REVEALERS = {"image": _reveal_from_image, "wav": _reveal_from_wav, "mp3": _reveal_from_mp3}


def _check_paths(carrier: str, output: str) -> str:
    kind = carrier_kind(carrier)
    if kind is None:
        raise WhisperError("Unsupported file type. Use a picture (PNG, BMP, JPG), a WAV or an MP3.")
    if not os.path.isfile(carrier):
        raise WhisperError("File not found: %s" % carrier)
    if os.path.abspath(output) == os.path.abspath(carrier):
        raise WhisperError("Save under a different name: overwriting the original would destroy it.")
    want = output_extension(carrier)
    if os.path.splitext(output)[1].lower() != want:
        raise WhisperError("The result must be saved as a %s file." % want.upper().lstrip("."))
    return kind


def hide_text(carrier: str, output: str, message: str, password: str) -> str:
    """Hide `message` in `carrier`, write the result to `output`."""
    if not isinstance(message, str) or message == "":
        raise WhisperError("Write the message you want to hide.")
    kind = _check_paths(carrier, output)
    if not password:
        raise WhisperError("Enter a password.")
    return _HIDERS[kind](carrier, output, password, KIND_TEXT, message.encode("utf-8"))


def hide_image(carrier: str, output: str, secret_image: str, password: str) -> str:
    """Hide a picture. It is stored as its original file if it fits, otherwise
    re-encoded (and if needed scaled down) until it does."""
    kind = _check_paths(carrier, output)
    if not password:
        raise WhisperError("Enter a password.")
    room = None if kind == "mp3" else capacity(carrier)
    data = _fit_secret_image(secret_image, room)
    return _HIDERS[kind](carrier, output, password, KIND_IMAGE, data)


def reveal(path: str, password: str) -> Revealed:
    """Recover what was hidden in `path`. Raises WrongPasswordOrEmpty when the
    password is wrong or nothing is hidden (deliberately indistinguishable)."""
    kind = carrier_kind(path)
    if kind is None:
        raise WhisperError("Unsupported file type.")
    if not os.path.isfile(path):
        raise WhisperError("File not found: %s" % path)
    if not password:
        raise WhisperError("Enter a password.")
    try:
        return _REVEALERS[kind](path, password)
    except WrongPasswordOrEmpty:
        from legacy import reveal_legacy, is_legacy_file
        if is_legacy_file(path):
            return reveal_legacy(path, password)
        raise


# --- secret pictures --------------------------------------------------------------------------

def _fit_secret_image(path: str, room: Optional[int]) -> bytes:
    try:
        with open(path, "rb") as f:
            original = f.read()
        img = Image.open(io.BytesIO(original))
        img.load()
    except FileNotFoundError:
        raise WhisperError("File not found: %s" % path)
    except Exception as exc:
        raise WhisperError("The picture to hide can't be opened (%s)." % exc)
    if (room is None or len(original) <= room) and max(img.size) <= MAX_SECRET_IMAGE_SIDE:
        return original                                   # exact original, any format
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGBA" if "transparency" in img.info or img.mode in ("LA", "PA") else "RGB")
    scale = min(1.0, MAX_SECRET_IMAGE_SIDE / float(max(img.size)))
    for _ in range(40):
        size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        candidate = img.resize(size, Image.Resampling.LANCZOS) if size != img.size else img
        for fmt, opts in (("PNG", {"optimize": True}), ("JPEG", {"quality": 88})):
            if fmt == "JPEG" and candidate.mode == "RGBA":
                continue
            buf = io.BytesIO()
            candidate.save(buf, format=fmt, **opts)
            if room is None or buf.tell() <= room:
                return buf.getvalue()
        scale *= 0.8
        if size == (1, 1):
            break
    raise WhisperError("This file is too small to hold a picture.")


# --- passwords ----------------------------------------------------------------------------------

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!#$%&*+-=?@^_~"


def generate_password(length: int = 20) -> str:
    """A random password from the OS CSPRNG with at least one of each class."""
    while True:
        pw = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw) and any(not c.isalnum() for c in pw)):
            return pw


def password_strength(password: str) -> tuple:
    """(score 0-4, label) -- a rough estimate for the strength meter."""
    if not password:
        return 0, ""
    pool = 0
    pool += 26 if any(c.islower() for c in password) else 0
    pool += 26 if any(c.isupper() for c in password) else 0
    pool += 10 if any(c.isdigit() for c in password) else 0
    pool += 32 if any(not c.isalnum() for c in password) else 0
    bits = len(password) * (np.log2(pool) if pool else 0)
    if len(set(password)) <= 2:
        bits = min(bits, 10)
    for limit, score, label in ((28, 0, "Very weak"), (40, 1, "Weak"), (60, 2, "Fair"), (80, 3, "Strong")):
        if bits < limit:
            return score, label
    return 4, "Very strong"


# --- small utilities ----------------------------------------------------------------------------

def human_bytes(count: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if count < 1024 or unit == "GB":
            return ("%d %s" % (count, unit)) if unit == "bytes" else ("%.1f %s" % (count, unit))
        count /= 1024.0


def _tmp_path(output: str) -> str:
    return output + ".whisper-tmp"


def _remove_quietly(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _atomic_save(output: str, writer) -> None:
    """Write to a temporary file and move it into place, so a failure never
    leaves a half-written result (or destroys an existing file)."""
    tmp = _tmp_path(output)
    try:
        with open(tmp, "wb") as f:
            writer(f)
        os.replace(tmp, output)
    except WhisperError:
        raise
    except OSError as exc:
        raise WhisperError("Couldn't save the file (%s)." % (exc.strerror or exc))
    except Exception as exc:
        raise WhisperError("Couldn't save the file (%s)." % exc)
    finally:
        _remove_quietly(tmp)

