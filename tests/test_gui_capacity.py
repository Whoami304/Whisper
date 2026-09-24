"""Pins gui/capacity.py against the real ciphers and the real writer.

The Hide window's budget meter is only useful if it is exact. It predicts
how large the ciphertext will be without running a cipher, so that it can
update on every keystroke; if that prediction drifts from what the engine
actually does, the meter tells the user a message fits and the embed then
fails, which is worse than having no meter at all.

Run from the project root:

    python -m unittest discover tests -v
"""

import os
import random
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "Whisper")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from gui import capacity
from StegoTextPass import StegoTextPass
from steganography import StegoError, TextSteganography

ALGOS = ("Weak", "Medium", "Strong")


class CiphertextPrediction(unittest.TestCase):
    """ciphertext_length() must equal what the cipher really emits."""

    def setUp(self):
        self.stego = StegoTextPass()

    def actual(self, text, algo_label):
        algo = self.stego.ui_algo_map[algo_label]
        return len(self.stego._encrypt(algo, text, "a-key").encode("utf-8"))

    def test_every_length(self):
        for algo in ALGOS:
            for length in (0, 1, 2, 15, 16, 17, 31, 32, 33, 100, 1000, 5000):
                text = "a" * length
                self.assertEqual(
                    capacity.ciphertext_length(text, algo), self.actual(text, algo),
                    "%s cipher, %d characters" % (algo, length))

    def test_non_ascii(self):
        samples = [
            "გამარჯობა",
            "café naïve",
            "\U0001F510\U0001F511\U0001F512",
            "mixed 日本語 and ascii",
        ]
        for algo in ALGOS:
            for text in samples:
                self.assertEqual(
                    capacity.ciphertext_length(text, algo), self.actual(text, algo),
                    "%s cipher, %r" % (algo, text[:20]))

    def test_control_characters(self):
        text = "a\x00b\nc\td"
        for algo in ALGOS:
            self.assertEqual(capacity.ciphertext_length(text, algo),
                             self.actual(text, algo), algo)


class EmbeddedBits(unittest.TestCase):
    """embedded_bits() must match the LSB writer's own arithmetic."""

    def test_matches_the_engine(self):
        stego = StegoTextPass()
        for algo in ALGOS:
            for length in (1, 10, 200, 3000):
                text = "a" * length
                blob = stego._encrypt(stego.ui_algo_map[algo], text, "a-key")
                self.assertEqual(capacity.embedded_bits(text, algo),
                                 TextSteganography.required_bits(blob),
                                 "%s cipher, %d characters" % (algo, length))

    def test_empty_payload_costs_nothing(self):
        for algo in ALGOS:
            self.assertEqual(capacity.embedded_bits("", algo), 0)


class CapacityBoundary(unittest.TestCase):
    """max_plaintext_bytes() must be the true edge: fits at N, fails at N+1."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="whisper_gui_tests_")

    def carrier(self, size, seed):
        from PIL import Image
        path = os.path.join(self.tmp, "carrier_%d_%d.png" % (size, seed))
        rng = random.Random(seed)
        image = Image.new("RGB", (size, size))
        image.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                       for _ in range(size * size)])
        image.save(path)
        return path

    def test_boundary_is_exact(self):
        stego = StegoTextPass()
        for size in (32, 48):
            path = self.carrier(size, size)
            bits = TextSteganography.capacity_bits(path)
            for algo in ALGOS:
                limit = capacity.max_plaintext_bytes(bits, algo)
                self.assertGreater(limit, 0)

                at_limit = os.path.join(self.tmp, "at_%d_%s.png" % (size, algo))
                stego.encode_text_with_password(path, "a" * limit, "pw", algo, at_limit)
                self.assertEqual(
                    StegoTextPass().decode_with_password(at_limit, "pw", "text"),
                    "a" * limit, "%s at the limit of a %dpx carrier" % (algo, size))

                over = os.path.join(self.tmp, "over_%d_%s.png" % (size, algo))
                with self.assertRaises(StegoError,
                                       msg="%s should refuse limit+1" % algo):
                    stego.encode_text_with_password(
                        path, "a" * (limit + 1), "pw", algo, over)
                self.assertFalse(os.path.exists(over),
                                 "a refused embed must leave no file behind")

    def test_zero_capacity(self):
        for algo in ALGOS:
            self.assertEqual(capacity.max_plaintext_bytes(0, algo), 0)


class ImageCapacity(unittest.TestCase):
    def test_header_plus_pixels(self):
        self.assertEqual(capacity.image_payload_bits(10, 10), 64 + 10 * 10 * 24)

    def test_carrier_capacity(self):
        self.assertEqual(capacity.image_capacity_bits(100, 50), 100 * 50 * 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
