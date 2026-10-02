import io
import os

import numpy as np
import pytest
from PIL import Image

import engine

PW = "correct horse battery staple"


@pytest.mark.parametrize("carrier_fixture,ext", [
    ("png", ".png"), ("rgba_png", ".png"), ("jpg", ".png"), ("wav", ".wav"), ("mp3", ".mp3")])
def test_text_roundtrip(request, tmp_path, carrier_fixture, ext):
    carrier = request.getfixturevalue(carrier_fixture)
    out = str(tmp_path / ("out" + ext))
    message = "Привет, 秘密 🔐\nline two"
    engine.hide_text(carrier, out, message, PW)
    result = engine.reveal(out, PW)
    assert result.text == message and result.image_bytes is None and not result.legacy


@pytest.mark.parametrize("carrier_fixture,ext", [("png", ".png"), ("wav", ".wav"), ("mp3", ".mp3")])
def test_image_roundtrip(request, tmp_path, secret_picture, carrier_fixture, ext):
    carrier = request.getfixturevalue(carrier_fixture)
    out = str(tmp_path / ("out" + ext))
    engine.hide_image(carrier, out, secret_picture, PW)
    result = engine.reveal(out, PW)
    assert result.text is None
    got = np.array(Image.open(io.BytesIO(result.image_bytes)).convert("RGB"))
    assert np.array_equal(got, np.array(Image.open(secret_picture).convert("RGB")))


@pytest.mark.parametrize("carrier_fixture,ext", [("png", ".png"), ("wav", ".wav"), ("mp3", ".mp3")])
def test_wrong_password_and_clean_file_look_the_same(request, tmp_path, carrier_fixture, ext):
    carrier = request.getfixturevalue(carrier_fixture)
    out = str(tmp_path / ("out" + ext))
    engine.hide_text(carrier, out, "secret", PW)
    with pytest.raises(engine.WrongPasswordOrEmpty) as wrong:
        engine.reveal(out, PW + "x")
    with pytest.raises(engine.WrongPasswordOrEmpty) as empty:
        engine.reveal(carrier, PW)
    assert str(wrong.value) == str(empty.value)


def test_image_changes_are_at_most_one_lsb(png, tmp_path):
    out = str(tmp_path / "out.png")
    engine.hide_text(png, out, "x" * 500, PW)
    a = np.array(Image.open(png)).astype(int)
    b = np.array(Image.open(out)).astype(int)
    assert a.shape == b.shape and np.abs(a - b).max() <= 1


def test_alpha_channel_untouched(rgba_png, tmp_path):
    out = str(tmp_path / "out.png")
    engine.hide_text(rgba_png, out, "alpha", PW)
    a, b = np.array(Image.open(rgba_png)), np.array(Image.open(out))
    assert b.shape[2] == 4 and np.array_equal(a[..., 3], b[..., 3])


def test_same_input_gives_different_output(png, tmp_path):
    o1, o2 = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    engine.hide_text(png, o1, "same", PW)
    engine.hide_text(png, o2, "same", PW)
    assert not np.array_equal(np.array(Image.open(o1)), np.array(Image.open(o2)))


def test_no_plaintext_markers_in_output(png, wav, mp3, tmp_path):
    for carrier, ext in ((png, ".png"), (wav, ".wav"), (mp3, ".mp3")):
        out = str(tmp_path / ("m" + ext))
        engine.hide_text(carrier, out, "FINDME-plaintext", PW)
        blob = open(out, "rb").read()
        for marker in (b"FINDME", b"--PASS--", b"--ALGO--", PW.encode()):
            assert marker not in blob


def test_tampering_is_detected(png, tmp_path):
    out = str(tmp_path / "out.png")
    engine.hide_text(png, out, "integrity" * 50, PW)
    arr = np.array(Image.open(out))
    arr ^= 1                                   # flip every LSB
    Image.fromarray(arr).save(out)
    with pytest.raises(engine.WhisperError):
        engine.reveal(out, PW)


def test_message_too_long(png, tmp_path):
    cap = engine.capacity(png)
    assert cap == engine.capacity_for_size(160, 120)
    with pytest.raises(engine.WhisperError):
        engine.hide_text(png, str(tmp_path / "o.png"), "a" * (cap + 1), PW)
    engine.hide_text(png, str(tmp_path / "o.png"), "a" * cap, PW)
    assert engine.reveal(str(tmp_path / "o.png"), PW).text == "a" * cap


def test_big_secret_picture_is_shrunk_to_fit(png, tmp_path):
    big = str(tmp_path / "big.png")
    rng = np.random.default_rng(9)
    Image.fromarray(rng.integers(0, 256, (400, 400, 3), dtype=np.uint8)).save(big)
    out = str(tmp_path / "o.png")
    engine.hide_image(png, out, big, PW)
    Image.open(io.BytesIO(engine.reveal(out, PW).image_bytes)).verify()


@pytest.mark.parametrize("call", [
    lambda c, o: engine.hide_text(c, o, "", PW),
    lambda c, o: engine.hide_text(c, o, "m", ""),
    lambda c, o: engine.hide_text(c, c, "m", PW),
    lambda c, o: engine.hide_text(c, o[:-4] + ".jpg", "m", PW),
    lambda c, o: engine.hide_text(c + ".missing.png", o, "m", PW),
    lambda c, o: engine.hide_text(c[:-4] + ".txt", o, "m", PW),
])
def test_bad_input_raises_whisper_error(png, tmp_path, call):
    with pytest.raises(engine.WhisperError):
        call(png, str(tmp_path / "o.png"))
    assert not os.path.exists(str(tmp_path / "o.png"))


def test_not_a_picture(tmp_path):
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not an image")
    with pytest.raises(engine.WhisperError):
        engine.reveal(str(fake), PW)
    with pytest.raises(engine.WhisperError):
        engine.capacity(str(fake))


def test_no_temp_files_left(png, tmp_path):
    engine.hide_text(png, str(tmp_path / "o.png"), "m", PW)
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".whisper-tmp")]


def test_password_helpers():
    pw = engine.generate_password()
    assert len(pw) == 20 and pw != engine.generate_password()
    assert engine.password_strength("")[0] == 0
    assert engine.password_strength("aaaa")[0] == 0
    assert engine.password_strength(pw)[0] == 4
