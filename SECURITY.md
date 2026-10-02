# Security notes

This document is for reviewers. It describes what Whisper v2 protects, how, and where its limits are.

## Threat model

| Adversary | Goal | Protected? |
|---|---|---|
| Has the file, not the password | Read the secret | **Yes** — AES-256-GCM, key from scrypt |
| Has the file, not the password | Modify the secret undetected | **Yes** — GCM authentication; any change fails to decrypt |
| Has the file, not the password | Prove a secret is present by inspecting the format | **Yes for PNG/WAV** — no header, marker, hash or plaintext length. **No for MP3** — a `TXXX:whisper` ID3 tag is visible |
| Statistical steganalysis (RS, chi-square, ML detectors) | Detect that LSBs were modified | **No** — LSB replacement is detectable, especially at high fill ratios. Whisper hides content, it does not guarantee undetectability |
| Brute force on a weak password | Read the secret | Slowed (scrypt N=2^15, r=8, p=1 ≈ 32 MB and ~100 ms per guess) but **not prevented**. The GUI shows a strength meter, warns about weak passwords and offers a generator |
| Lossy re-encoding (messengers, social networks) | — | Destroys the secret (PNG/WAV must be shared as files) |

## Format (v2)

```
keys        = scrypt(password, salt16, N=2^15, r=8, p=1, dklen=52)
              -> aes_key[32] | scatter_key[16] | length_mask[4]
plaintext   = kind[1] (1 = UTF-8 text, 2 = encoded picture) || data
sealed      = AES-256-GCM(aes_key, nonce12, plaintext, aad = "WHISPER-v2")
record      = (len(nonce||sealed) XOR length_mask)[4] || nonce[12] || sealed
```

**PNG / WAV.** The 16-byte random salt is written to the LSBs of the first 128 sample slots
(colour values R,G,B — alpha is never touched — or PCM samples). The record bits go into slots
chosen by a keyed pseudo-random permutation (6-round Feistel network over the slot index,
cycle-walking to the exact domain size, round keys from `scatter_key`). Unused slots are not modified.
Each pixel/sample changes by at most 1.

**MP3.** LSB embedding cannot survive MP3 quantisation, so `base64(salt || record)` is stored in an
ID3v2.3 `TXXX` frame with description `whisper`. Confidentiality and integrity are the same; presence is not hidden.

**Reading.** Wrong password, tampered data and "nothing hidden" all raise the same
`WrongPasswordOrEmpty` error with the same message.

**Writing.** Output is written to `<name>.whisper-tmp` and atomically renamed; the carrier file is
never modified, and writing over the carrier is refused.

## Known limitations

- The salt occupies fixed positions (first 128 slots). It is random and indistinguishable from
  natural LSB noise, but its location is public.
- LSB replacement is detectable by steganalysis (see the table).
- Secret pictures larger than the free space are re-encoded (PNG → JPEG, then downscaled) to fit.
- Python strings holding the password and plaintext cannot be reliably wiped from memory.
- No authentication of *who* made a file — anyone with the password can create a valid one.

## Whisper v1 (legacy, read-only)

v1 is kept only so existing files can be opened (`Whisper/legacy.py`); **v2 never writes it**. Its weaknesses:

- Plaintext trailer `--PASS--<sha256(password)>--ALGO--<name>` appended to every file: reveals that a
  secret is present and allows fast offline password cracking (unsalted SHA-256).
- "Ciphers" `reverse` (hex + reverse) and `caser` (Caesar shift) offer no confidentiality.
- AES-CBC with key = SHA-256(password), no KDF, no authentication.
- Hidden pictures were not encrypted at all; data was written sequentially from the first pixel.

The app shows a notice recommending re-hiding when it opens a v1 file.

## Reporting

Please open a GitHub issue (or contact the maintainer privately for anything sensitive).
