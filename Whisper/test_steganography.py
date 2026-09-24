"""
Whisper-ის სტეგანოგრაფიის მოდულის ტესტები.

გაშვება პროექტის Whisper საქაღალდიდან:
    python -m unittest test_steganography -v

ტესტები მუშაობს დროებით საქაღალდეში და პროექტის ფაილებს არ ცვლის.
"""

import io
import os
import random
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

from AudioTextSteganography import AudioTextSteganography
from ImageSteganography import ImageSteganography
from StegoTextPass import StegoTextPass
from steganography import StegoError, TextSteganography

ALGO_LABELS = ("Weak", "Medium", "Strong")


def quiet(func, *args, **kwargs):
    """ტესტების გამოტანა სუფთა რომ დარჩეს, მოდულის print-ები იჭერს."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def make_image(path, width, height, seed=None, flat=None):
    image = Image.new("RGB", (width, height))
    if flat is not None:
        image.paste(flat, (0, 0, width, height))
    else:
        rng = random.Random(seed)
        image.putdata([
            (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            for _ in range(width * height)
        ])
    image.save(path)
    return path


def pixels(image):
    return list(image.convert("RGB").getdata())


class StegoTestCase(unittest.TestCase):
    """საერთო დროებითი საქაღალდე და დამხმარე გზები."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="whisper_tests_")
        cls.cover = make_image(os.path.join(cls.tmp, "cover.png"), 200, 200, seed=1)
        cls.secret = make_image(os.path.join(cls.tmp, "secret.png"), 20, 20, seed=2)
        source_audio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "turbo.mp3")
        cls.audio = os.path.join(cls.tmp, "carrier.mp3")
        cls.has_audio = os.path.exists(source_audio)
        if cls.has_audio:
            shutil.copyfile(source_audio, cls.audio)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def out(self, name):
        return os.path.join(self.tmp, name)


class TextInImageRoundTrip(StegoTestCase):
    """ტექსტი ფოტოში: ჩამალული და ამოღებული ტექსტი ზუსტად უნდა დაემთხვეს."""

    def roundtrip(self, message, password="pa55word!", algo="Strong", carrier=None, name=None):
        stego = StegoTextPass()
        output = self.out(name or f"rt_{abs(hash((message, algo))) % 10**8}.png")
        quiet(stego.encode_text_with_password,
              carrier or self.cover, message, password, algo, output)
        # გაშიფრვა ახალ ობიექტზე ხდება, რომ არცერთი მდგომარეობა არ გადავიდეს
        extracted, _ = quiet(StegoTextPass().decode_with_password, output, password, "text")
        return extracted

    def test_single_character(self):
        self.assertEqual(self.roundtrip("A"), "A")

    def test_normal_message(self):
        message = "Hello, this is a secret message!"
        self.assertEqual(self.roundtrip(message), message)

    def test_large_payload(self):
        message = "".join(random.Random(7).choice("abcdefgh ") for _ in range(5000))
        self.assertEqual(self.roundtrip(message), message)

    def test_non_ascii(self):
        message = "გამარჯობა 日本語 éü \U0001F600"
        self.assertEqual(self.roundtrip(message), message)

    def test_null_bytes(self):
        message = "a\x00b\x00\x00c"
        self.assertEqual(self.roundtrip(message), message)

    def test_random_binary_as_latin1_text(self):
        raw = bytes(random.Random(3).randrange(256) for _ in range(400))
        message = raw.decode("latin-1")
        self.assertEqual(self.roundtrip(message), message)

    def test_payload_containing_the_trailer_markers(self):
        # მარკერები ტექსტში არ უნდა არღვევდეს ფაილის დაშლას
        message = "data\n--PASS--\nfake\n--ALGO--\naes"
        self.assertEqual(self.roundtrip(message), message)

    def test_all_algorithms_survive_a_fresh_process_state(self):
        message = "The same key must always work."
        for algo in ALGO_LABELS:
            with self.subTest(algo=algo):
                self.assertEqual(self.roundtrip(message, algo=algo, name=f"algo_{algo}.png"), message)

    def test_caesar_shift_is_deterministic_per_password(self):
        # "Weak" ადრე რანდომ shift-ს იყენებდა და სხვა ობიექტზე ნაგავს აბრუნებდა
        from protection import PasswordProtection
        first, second = PasswordProtection(), PasswordProtection()
        self.assertEqual(first.shift_for("hunter2"), second.shift_for("hunter2"))

    def test_text_file_is_not_written_into_the_source_carrier(self):
        before = open(self.cover, "rb").read()
        self.roundtrip("does not touch the carrier", name="carrier_check.png")
        self.assertEqual(open(self.cover, "rb").read(), before)


class TextInAudioRoundTrip(StegoTestCase):
    """ტექსტი აუდიოში."""

    def setUp(self):
        if not self.has_audio:
            self.skipTest("img/turbo.mp3 is not available")

    def roundtrip(self, message, algo, password="pa55word!"):
        stego = StegoTextPass()
        output = self.out(f"audio_{algo}.mp3")
        quiet(stego.encode_audio_with_password, self.audio, message, password, algo, output)
        extracted, _ = quiet(StegoTextPass().decode_with_password, output, password, "audio")
        return extracted

    def test_every_algorithm_round_trips(self):
        message = "Hello from the audio carrier!"
        for algo in ALGO_LABELS:
            with self.subTest(algo=algo):
                self.assertEqual(self.roundtrip(message, algo), message)

    def test_non_ascii_in_audio(self):
        message = "გამარჯობა from ID3"
        self.assertEqual(self.roundtrip(message, "Strong"), message)

    def test_check_content(self):
        output = self.out("audio_check.mp3")
        quiet(StegoTextPass().encode_audio_with_password,
              self.audio, "hidden", "pw", "Strong", output)
        audio = AudioTextSteganography()
        self.assertTrue(quiet(audio.Check_Content, output)[0])
        self.assertFalse(quiet(audio.Check_Content, self.audio)[0])

    def test_empty_message_is_rejected(self):
        audio = AudioTextSteganography()
        with self.assertRaises(StegoError):
            quiet(audio.encode_info, "", self.audio, self.out("never.mp3"))
        self.assertFalse(os.path.exists(self.out("never.mp3")))

    def test_missing_carrier_is_rejected(self):
        audio = AudioTextSteganography()
        with self.assertRaises(StegoError):
            quiet(audio.encode_info, "x", self.out("nope.mp3"), self.out("never2.mp3"))


class ImageInImageRoundTrip(StegoTestCase):
    """ფოტო ფოტოში: პიქსელები ბაიტ-ბაიტ უნდა დაემთხვეს."""

    def test_exact_pixels_for_every_num_lsb(self):
        original = Image.open(self.secret)
        for num_lsb in range(1, 9):
            with self.subTest(num_lsb=num_lsb):
                steg = ImageSteganography(num_lsb=num_lsb)
                output = self.out(f"ii_{num_lsb}.png")
                quiet(steg.encode_info, self.cover, self.secret, output)
                decoded, _ = quiet(steg.decode_info, output)
                self.assertIsNotNone(decoded)
                self.assertEqual(pixels(decoded), pixels(original))

    def test_capacity_boundary_exact_fit(self):
        """
        ზუსტად ტევადობაზე მორგებული ფოტო უნდა აღდგეს უცვლელად.
        აქ ჩნდებოდა ბოლო, არასრული ჯგუფის ჩაწერის შეცდომა.
        """
        for num_lsb in range(1, 9):
            with self.subTest(num_lsb=num_lsb):
                cover = make_image(self.out(f"cap_cover_{num_lsb}.png"), 60, 60, seed=num_lsb)
                capacity = 60 * 60 * 3 * num_lsb
                max_pixels = (capacity - 64) // 24
                width = max(1, int(max_pixels ** 0.5))
                height = max_pixels // width
                secret = make_image(self.out(f"cap_secret_{num_lsb}.png"),
                                    width, height, seed=num_lsb + 100)
                steg = ImageSteganography(num_lsb=num_lsb)
                output = self.out(f"cap_out_{num_lsb}.png")
                quiet(steg.encode_info, cover, secret, output)
                decoded, _ = quiet(steg.decode_info, output)
                self.assertIsNotNone(decoded)
                self.assertEqual(decoded.size, (width, height))
                self.assertEqual(pixels(decoded), pixels(Image.open(secret)))

    def test_capacity_minus_one_pixel_row(self):
        cover = make_image(self.out("capm_cover.png"), 60, 60, seed=11)
        capacity = 60 * 60 * 3
        max_pixels = (capacity - 64) // 24 - 1
        width = max(1, int(max_pixels ** 0.5))
        height = max_pixels // width
        secret = make_image(self.out("capm_secret.png"), width, height, seed=12)
        steg = ImageSteganography(num_lsb=1)
        output = self.out("capm_out.png")
        quiet(steg.encode_info, cover, secret, output)
        decoded, _ = quiet(steg.decode_info, output)
        self.assertEqual(pixels(decoded), pixels(Image.open(secret)))

    def test_oversized_secret_is_downscaled_not_corrupted(self):
        """
        ზედმეტად დიდი ფოტო შეგნებულად მცირდება. მთავარია, რომ სათაურში
        ჩაწერილი ზომა და ამოღებული ფოტო ერთმანეთს დაემთხვეს.
        """
        big = make_image(self.out("big_secret.png"), 300, 300, seed=13)
        steg = ImageSteganography(num_lsb=1)
        output = self.out("big_out.png")
        quiet(steg.encode_info, self.cover, big, output)
        decoded, _ = quiet(steg.decode_info, output)
        self.assertIsNotNone(decoded)
        self.assertLess(decoded.size[0] * decoded.size[1], 300 * 300)

    def test_container_too_small_raises_and_writes_nothing(self):
        tiny = make_image(self.out("tiny.png"), 2, 2, seed=14)
        steg = ImageSteganography(num_lsb=1)
        output = self.out("tiny_out.png")
        with self.assertRaises(StegoError):
            quiet(steg.encode_info, tiny, self.secret, output)
        self.assertFalse(os.path.exists(output))

    def test_password_wrapper_round_trip(self):
        stego = StegoTextPass()
        output = self.out("ii_pass.png")
        quiet(stego.encode_image_with_password,
              self.cover, self.secret, "pw!1", "Strong", output)
        decoded, _ = quiet(StegoTextPass().decode_with_password, output, "pw!1", "image")
        self.assertIsNotNone(decoded)
        self.assertEqual(pixels(decoded), pixels(Image.open(self.secret)))

    def test_password_wrapper_rejects_too_small_container(self):
        tiny = make_image(self.out("tiny2.png"), 2, 2, seed=15)
        output = self.out("tiny2_out.png")
        with self.assertRaises(StegoError):
            quiet(StegoTextPass().encode_image_with_password,
                  tiny, self.secret, "pw", "Strong", output)
        self.assertFalse(os.path.exists(output))

    def test_check_content(self):
        steg = ImageSteganography(num_lsb=1)
        output = self.out("cc_out.png")
        quiet(steg.encode_info, self.cover, self.secret, output)
        self.assertIs(quiet(steg.check_content, output)[0], True)
        self.assertIs(quiet(steg.check_content, self.cover)[0], False)

    def test_only_the_low_bits_of_the_carrier_change(self):
        """ჩამალვა კონტეინერის დანარჩენ ბიტებს არ უნდა შეეხოს."""
        for num_lsb in (1, 2, 4):
            with self.subTest(num_lsb=num_lsb):
                steg = ImageSteganography(num_lsb=num_lsb)
                output = self.out(f"integrity_{num_lsb}.png")
                quiet(steg.encode_info, self.cover, self.secret, output)
                high_mask = 0xFF & ~((1 << num_lsb) - 1)
                before = pixels(Image.open(self.cover))
                after = pixels(Image.open(output))
                self.assertEqual(len(before), len(after))
                for original, encoded in zip(before, after):
                    for channel_before, channel_after in zip(original, encoded):
                        self.assertEqual(channel_before & high_mask, channel_after & high_mask)

    def test_pixels_past_the_payload_are_untouched(self):
        steg = ImageSteganography(num_lsb=1)
        output = self.out("tail_untouched.png")
        quiet(steg.encode_info, self.cover, self.secret, output)
        payload_channels = (64 + 20 * 20 * 24)  # num_lsb=1 -> ერთი ბიტი თითო არხზე
        before = pixels(Image.open(self.cover))
        after = pixels(Image.open(output))
        first_untouched_pixel = payload_channels // 3 + 1
        self.assertEqual(before[first_untouched_pixel:], after[first_untouched_pixel:])

    def test_decoding_does_not_modify_the_stego_file(self):
        steg = ImageSteganography(num_lsb=1)
        output = self.out("immutable.png")
        quiet(steg.encode_info, self.cover, self.secret, output)
        before = open(output, "rb").read()
        quiet(steg.decode_info, output)
        self.assertEqual(open(output, "rb").read(), before)


class CapacityAndBoundaries(StegoTestCase):
    """ტექსტის ტევადობის ზუსტი საზღვრები."""

    def usable_capacity_chars(self, carrier):
        """ყველაზე დიდი ლათინური ტექსტი, რომელიც ჯერ კიდევ ეტევა."""
        capacity = TextSteganography.capacity_bits(carrier)
        low, high = 0, capacity // 8 + 16
        while low < high:
            mid = (low + high + 1) // 2
            if TextSteganography.required_bits("a" * mid) <= capacity:
                low = mid
            else:
                high = mid - 1
        return low

    def test_exact_capacity_and_one_over(self):
        carrier = make_image(self.out("cap_text.png"), 40, 40, seed=21)
        limit = self.usable_capacity_chars(carrier)
        steg = TextSteganography()

        # ტევადობა - 1
        quiet(steg.encode_info, carrier, "a" * (limit - 1), self.out("cap_m1.png"))
        self.assertEqual(quiet(steg.decode_info, self.out("cap_m1.png"))[0], "a" * (limit - 1))

        # ზუსტად ტევადობა
        quiet(steg.encode_info, carrier, "a" * limit, self.out("cap_eq.png"))
        self.assertEqual(quiet(steg.decode_info, self.out("cap_eq.png"))[0], "a" * limit)

        # ტევადობა + 1 — სუფთად უნდა ჩავარდეს და ფაილი არ უნდა შექმნას
        over = self.out("cap_p1.png")
        with self.assertRaises(StegoError):
            quiet(steg.encode_info, carrier, "a" * (limit + 1), over)
        self.assertFalse(os.path.exists(over))

    def test_oversized_payload_through_the_password_api(self):
        carrier = make_image(self.out("cap_small.png"), 20, 20, seed=22)
        output = self.out("cap_over.png")
        with self.assertRaises(StegoError):
            quiet(StegoTextPass().encode_text_with_password,
                  carrier, "x" * 50000, "pw", "Strong", output)
        self.assertFalse(os.path.exists(output))

    def test_empty_payload_is_rejected_at_the_steg_layer(self):
        steg = TextSteganography()
        with self.assertRaises(StegoError):
            quiet(steg.encode_info, self.cover, "", self.out("never3.png"))

    def test_empty_payload_round_trips_through_the_password_api(self):
        # AES-ის შიფრტექსტი არასოდესაა ცარიელი, ამიტომ ცარიელი ტექსტიც ჩაიმალება
        output = self.out("empty_ok.png")
        quiet(StegoTextPass().encode_text_with_password,
              self.cover, "", "pw", "Strong", output)
        extracted, _ = quiet(StegoTextPass().decode_with_password, output, "pw", "text")
        self.assertEqual(extracted, "")


class KeyBehaviour(StegoTestCase):
    """პაროლის ქცევა."""

    def make_stego_file(self, algo="Strong", password="right-pass1!", message="top secret"):
        output = self.out(f"key_{algo}_{abs(hash(password)) % 10**6}.png")
        quiet(StegoTextPass().encode_text_with_password,
              self.cover, message, password, algo, output)
        return output, message

    def test_wrong_password_is_rejected_for_every_algorithm(self):
        for algo in ALGO_LABELS:
            with self.subTest(algo=algo):
                path, _ = self.make_stego_file(algo=algo)
                result, _ = quiet(StegoTextPass().decode_with_password, path, "wrong-pass", "text")
                self.assertIsNone(result, "a wrong password must not return content")

    def test_random_passwords_never_succeed(self):
        path, message = self.make_stego_file()
        rng = random.Random(31)
        for _ in range(25):
            candidate = "".join(rng.choice("abcdefghijklmnop0123456789") for _ in range(12))
            result, _ = quiet(StegoTextPass().decode_with_password, path, candidate, "text")
            self.assertIsNone(result)
        # სწორი პაროლი კი კვლავ მუშაობს
        self.assertEqual(
            quiet(StegoTextPass().decode_with_password, path, "right-pass1!", "text")[0], message)

    def test_empty_password_works_and_only_matches_itself(self):
        path, message = self.make_stego_file(password="")
        self.assertEqual(quiet(StegoTextPass().decode_with_password, path, "", "text")[0], message)
        self.assertIsNone(quiet(StegoTextPass().decode_with_password, path, " ", "text")[0])

    def test_unicode_password(self):
        password = "პაროლი-1!"
        path, message = self.make_stego_file(password=password)
        self.assertEqual(
            quiet(StegoTextPass().decode_with_password, path, password, "text")[0], message)

    def test_password_is_never_printed(self):
        password = "Sup3rSecret!"
        output = self.out("leak.png")
        _, encode_log = quiet(StegoTextPass().encode_text_with_password,
                              self.cover, "payload", password, "Strong", output)
        _, decode_log = quiet(StegoTextPass().decode_with_password, output, password, "text")
        self.assertNotIn(password, encode_log)
        self.assertNotIn(password, decode_log)

    def test_hidden_content_is_never_printed(self):
        secret_text = "NUCLEAR-LAUNCH-CODE-42"
        output = self.out("leak2.png")
        quiet(StegoTextPass().encode_text_with_password,
              self.cover, secret_text, "pw", "Strong", output)
        _, decode_log = quiet(StegoTextPass().decode_with_password, output, "pw", "text")
        self.assertNotIn(secret_text, decode_log)

    def test_process_password_does_not_echo_the_password(self):
        from protection import PasswordProtection
        password = "Weak1!"
        _, message = PasswordProtection().process_password(password)
        self.assertNotIn(password, message)


class DestructiveInput(StegoTestCase):
    """განზრახ გატეხვის მცდელობები — ყველა უნდა ჩავარდეს სუფთად."""

    def setUp(self):
        self.good = self.out("destructive.png")
        if not os.path.exists(self.good):
            quiet(StegoTextPass().encode_text_with_password,
                  self.cover, "intact message", "pw1!", "Strong", self.good)

    def decode(self, path, password="pw1!", data_type="text"):
        return quiet(StegoTextPass().decode_with_password, path, password, data_type)[0]

    def test_missing_file(self):
        self.assertIsNone(self.decode(self.out("does_not_exist.png")))

    def test_empty_file(self):
        path = self.out("zero.png")
        open(path, "wb").close()
        self.assertIsNone(self.decode(path))

    def test_file_that_is_not_an_image(self):
        path = self.out("garbage.png")
        open(path, "wb").write(b"this is definitely not a PNG")
        self.assertIsNone(self.decode(path))

    def test_carrier_without_any_hidden_data(self):
        self.assertIsNone(self.decode(self.cover))

    def test_truncated_file(self):
        data = open(self.good, "rb").read()
        path = self.out("truncated.png")
        open(path, "wb").write(data[: len(data) // 2])
        self.assertIsNone(self.decode(path))

    def test_corrupted_pixel_data(self):
        data = bytearray(open(self.good, "rb").read())
        for index in range(120, min(600, len(data))):
            data[index] ^= 0xFF
        path = self.out("corrupted.png")
        open(path, "wb").write(bytes(data))
        self.assertIsNone(self.decode(path))

    def test_corrupted_trailer(self):
        data = open(self.good, "rb").read()
        path = self.out("bad_trailer.png")
        open(path, "wb").write(data.replace(b"\n--ALGO--\n", b"\n--ALGZ--\n"))
        self.assertIsNone(self.decode(path))

    def test_tampered_password_hash(self):
        data = open(self.good, "rb").read()
        head, tail = data.rsplit(b"\n--PASS--\n", 1)
        digest, algo = tail.split(b"\n--ALGO--\n", 1)
        tampered = head + b"\n--PASS--\n" + b"f" * len(digest) + b"\n--ALGO--\n" + algo
        path = self.out("tampered_hash.png")
        open(path, "wb").write(tampered)
        self.assertIsNone(self.decode(path))

    def test_unknown_algorithm_label(self):
        data = open(self.good, "rb").read()
        path = self.out("bad_algo.png")
        open(path, "wb").write(data.rsplit(b"\n--ALGO--\n", 1)[0] + b"\n--ALGO--\nrot13")
        self.assertIsNone(self.decode(path))

    def test_unsupported_data_type(self):
        self.assertIsNone(self.decode(self.good, data_type="video"))

    def test_unsupported_carrier_extension(self):
        path = self.out("carrier.txt")
        open(path, "w", encoding="utf-8").write("just some text")
        with self.assertRaises(ValueError):
            quiet(StegoTextPass().encode_text_with_password,
                  path, "msg", "pw", "Strong", self.out("out.txt"))
        self.assertFalse(os.path.exists(self.out("out.txt")))

    def test_unusual_filename(self):
        weird = self.out("a b (1) #ü'&.png")
        quiet(StegoTextPass().encode_text_with_password,
              self.cover, "odd name", "pw", "Strong", weird)
        self.assertEqual(self.decode(weird, password="pw"), "odd name")

    def test_repeated_encode_decode_cycles(self):
        message = "cycle payload"
        current = self.cover
        for cycle in range(5):
            output = self.out(f"cycle_{cycle}.png")
            quiet(StegoTextPass().encode_text_with_password,
                  current, message, "pw", "Strong", output)
            self.assertEqual(self.decode(output, password="pw"), message)
            current = output

    def test_many_consecutive_operations_on_one_instance(self):
        stego = StegoTextPass()
        for index in range(10):
            message = f"message number {index}"
            output = self.out(f"consecutive_{index}.png")
            quiet(stego.encode_text_with_password,
                  self.cover, message, f"pw{index}", "Strong", output)
            self.assertEqual(
                quiet(stego.decode_with_password, output, f"pw{index}", "text")[0], message)

    def test_image_decode_on_a_text_stego_file(self):
        self.assertIsNone(self.decode(self.good, data_type="image"))

    def test_text_decode_on_an_image_stego_file(self):
        output = self.out("image_stego.png")
        quiet(StegoTextPass().encode_image_with_password,
              self.cover, self.secret, "pw", "Strong", output)
        self.assertIsNone(self.decode(output, password="pw", data_type="text"))


class ConsoleOutput(StegoTestCase):
    """ჩვენება Windows-ის კონსოლზეც უნდა მუშაობდეს."""

    def test_module_messages_are_cp1252_safe(self):
        output = self.out("console.png")
        _, encode_log = quiet(StegoTextPass().encode_text_with_password,
                              self.cover, "console check", "pw", "Strong", output)
        _, decode_log = quiet(StegoTextPass().decode_with_password, output, "pw", "text")
        _, fail_log = quiet(StegoTextPass().decode_with_password, output, "nope", "text")
        for log in (encode_log, decode_log, fail_log):
            log.encode("cp1252")  # ემოჯი აქ UnicodeEncodeError-ს ისროდა


if __name__ == "__main__":
    unittest.main(verbosity=2)
