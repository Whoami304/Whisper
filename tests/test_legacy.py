import io
import os

import numpy as np
import pytest
from PIL import Image

import engine
from conftest import FIXTURES

PW = "old-pass-1"


@pytest.mark.parametrize("name", ["v1_text_aes.png", "v1_text_reverse.png", "v1_text_caser.png"])
def test_v1_text(name):
    result = engine.reveal(os.path.join(FIXTURES, name), PW)
    assert result.legacy and result.text.startswith("v1 secret via ")


def test_v1_mp3():
    result = engine.reveal(os.path.join(FIXTURES, "v1_text_aes.mp3"), PW)
    assert result.legacy and result.text == "v1 mp3 secret"


def test_v1_image():
    result = engine.reveal(os.path.join(FIXTURES, "v1_image.png"), PW)
    got = np.array(Image.open(io.BytesIO(result.image_bytes)).convert("RGB"))
    want = np.array(Image.open(os.path.join(FIXTURES, "v1_image_expected.png")).convert("RGB"))
    assert result.legacy and np.array_equal(got, want)


def test_v1_wrong_password():
    with pytest.raises(engine.WhisperError):
        engine.reveal(os.path.join(FIXTURES, "v1_text_aes.png"), "nope")
