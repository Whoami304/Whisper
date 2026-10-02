import os
import sys
import wave

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "Whisper")):
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


@pytest.fixture
def png(tmp_path):
    rng = np.random.default_rng(1)
    path = tmp_path / "carrier.png"
    Image.fromarray(rng.integers(0, 256, (120, 160, 3), dtype=np.uint8)).save(path)
    return str(path)


@pytest.fixture
def rgba_png(tmp_path):
    rng = np.random.default_rng(2)
    arr = rng.integers(0, 256, (80, 100, 4), dtype=np.uint8)
    path = tmp_path / "carrier_rgba.png"
    Image.fromarray(arr, "RGBA").save(path)
    return str(path)


@pytest.fixture
def jpg(tmp_path):
    rng = np.random.default_rng(3)
    path = tmp_path / "carrier.jpg"
    Image.fromarray(rng.integers(0, 256, (90, 90, 3), dtype=np.uint8)).save(path, quality=90)
    return str(path)


@pytest.fixture
def wav(tmp_path):
    path = tmp_path / "carrier.wav"
    t = np.arange(44100) / 44100.0
    samples = (np.sin(2 * np.pi * 440 * t) * 12000).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(samples.tobytes())
    return str(path)


@pytest.fixture
def mp3(tmp_path):
    # A few silent MPEG-1 Layer III frames are enough for ID3 tagging.
    path = tmp_path / "carrier.mp3"
    frame = b"\xff\xfb\x90\x64" + b"\x00" * 413
    path.write_bytes(frame * 20)
    return str(path)


@pytest.fixture
def secret_picture(tmp_path):
    path = tmp_path / "secret.png"
    arr = np.zeros((30, 40, 3), dtype=np.uint8)
    arr[:, :20] = (200, 30, 30)
    Image.fromarray(arr).save(path)
    return str(path)
