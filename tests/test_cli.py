import os

import main as cli


def test_cli_roundtrip(png, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHISPER_PASSWORD", "cli-password-123!")
    out = str(tmp_path / "o.png")
    assert cli.main(["hide-text", png, out, "-m", "hello cli"]) == 0
    capsys.readouterr()
    assert cli.main(["reveal", out]) == 0
    assert "hello cli" in capsys.readouterr().out


def test_cli_image_and_capacity(png, secret_picture, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHISPER_PASSWORD", "cli-password-123!")
    out = str(tmp_path / "o.png")
    assert cli.main(["hide-image", png, out, secret_picture]) == 0
    dest = str(tmp_path / "back.png")
    assert cli.main(["reveal", out, "-o", dest]) == 0
    assert os.path.getsize(dest) > 0
    assert cli.main(["reveal", out, "-o", dest]) == 1          # refuses to overwrite
    assert cli.main(["capacity", png]) == 0


def test_cli_errors_are_clean(png, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WHISPER_PASSWORD", "wrong")
    assert cli.main(["reveal", png]) == 1
    assert "Error:" in capsys.readouterr().err
