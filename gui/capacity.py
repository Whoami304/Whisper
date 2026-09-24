"""Capacity arithmetic for the Hide window's budget meter.

The meter has to measure what is actually written into the carrier, and
that is the *ciphertext*, not the text the user typed. The three ciphers
expand a payload very differently -- "Medium" doubles it, "Strong" grows
it by roughly a third plus a block -- so a meter reading the plaintext
would show a message fitting and then the embed would fail.

No password is needed for any of this: every expansion is a function of
length alone, so the numbers can be recomputed on every keystroke without
running a cipher.

This lives in the GUI layer rather than in the engine because it is a
presentation concern -- the engine already refuses an oversized payload
on its own. The predictions are pinned against the real ciphers by
tests/test_gui_capacity.py, so if a cipher ever changes, that test fails
rather than the meter quietly lying.
"""

def ciphertext_length(text, algo_label):
    """Bytes the chosen cipher will produce for `text`, without running it."""
    raw = len(text.encode("utf-8"))

    if algo_label == "Weak":
        # Caesar over string.printable: every printable ASCII character
        # maps to another one, and anything outside the alphabet is
        # passed through untouched, so the byte count never changes.
        return raw
    if algo_label == "Medium":
        # The reverse cipher hexes the UTF-8 bytes: two ASCII characters
        # per byte.
        return raw * 2
    # "Strong" is AES-256-CBC: a 16-byte random IV, then PKCS#7 padding up
    # to the next whole block (a full extra block when the text already
    # lands on a boundary), then Base64 at 4 characters per 3 bytes.
    blocks = (raw // 16) + 1
    return ((16 + blocks * 16) + 2) // 3 * 4


def embedded_bits(text, algo_label):
    """Bits the payload occupies in a PNG once encrypted.

    Mirrors what the LSB writer does with the ciphertext: a
    "<byte count>:" prefix, the data as UTF-8, then padding up to a
    multiple of three, because one pixel carries three bits.
    """
    if not text:
        return 0
    payload = ciphertext_length(text, algo_label)
    # The prefix counts the ciphertext's bytes; the ciphertext is ASCII
    # for every cipher here, so its byte length equals its character
    # length and the prefix can be measured from the number alone.
    prefix = len("%d:" % payload)
    bits = (prefix + payload) * 8
    return bits + ((3 - (bits % 3)) % 3)


def max_plaintext_bytes(capacity_bits, algo_label):
    """The largest plaintext, in UTF-8 bytes, that still fits.

    Found by bisection over embedded_bits() rather than by inverting the
    padding arithmetic, so the two can never drift apart.
    """
    if capacity_bits <= 0:
        return 0
    low, high = 0, capacity_bits // 8 + 64
    while low < high:
        mid = (low + high + 1) // 2
        if embedded_bits("a" * mid, algo_label) <= capacity_bits:
            low = mid
        else:
            high = mid - 1
    return low


def image_payload_bits(width, height, num_lsb=1):
    """Bits a secret image occupies: a 64-bit header plus 24 bits a pixel."""
    return 64 + width * height * 24


def image_capacity_bits(carrier_width, carrier_height, num_lsb=1):
    """A carrier's capacity for the image-in-image path."""
    return carrier_width * carrier_height * 3 * num_lsb
