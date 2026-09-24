import os
import base64
import hashlib
import hmac
import traceback
from AESCipher import AESCipher
from Reverse_Crypt import ReverseCrypt
from Cryptography import CaserCipher
from protection import PasswordProtection
from ImageSteganography import ImageSteganography
from AudioTextSteganography import AudioTextSteganography
from steganography import TextSteganography, StegoError

# დაშიფრული ტექსტის შემდეგ ფაილს ბოლოში ემატება პაროლის ჰეშიც და ალგორითმის სახელიც
PASS_MARKER = b"\n--PASS--\n"
ALGO_MARKER = b"\n--ALGO--\n"

class StegoTextPass:
    def __init__(self):
        self.prot = PasswordProtection()
        self.aes = AESCipher()
        self.reverse = ReverseCrypt()
        self.caser = CaserCipher()
        self.text_steg = TextSteganography()
        self.image_steg = ImageSteganography()
        self.audio_steg = AudioTextSteganography()

        self.ui_algo_map = {
            "Weak": "caser",
            "Medium": "reverse",
            "Strong": "aes"
        }

    def _encrypt(self, algo: str, text: str, password: str) -> str: # ADD 'password: str'
        if algo == "aes":
            self.aes._derive_key(password) # CORRECTED: Use password for key derivation
            encrypted_bytes = self.aes.encrypt(text)
            if not isinstance(encrypted_bytes, bytes):
                raise ValueError("Encryption failed.")
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        elif algo == "reverse":
            return self.reverse.Encrypt(text)
        elif algo == "caser":
            # სიგრძე პაროლიდან გამოითვლება. self.prot.shift რანდომადაა აღებული და
            # ყოველ გაშვებაზე იცვლებოდა, ამიტომ სხვა პროცესში გაშიფრვა ნაგავს აბრუნებდა.
            return self.caser.Encrypt(text, shift=self.prot.shift_for(password))
        else:
            raise ValueError("Unsupported encryption algorithm")
        
    

    def _decrypt(self, algo: str, encrypted_text: str, password: str) -> str:
        if not isinstance(encrypted_text, str):
            raise ValueError("Decryption error: extracted content is not text.")

        if algo == "aes":
            self.aes._derive_key(password)
            try:
                # Clean and decode Base64
                valid_b64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
                clean_base64 = ''.join(c for c in encrypted_text if c in valid_b64_chars)
                encrypted_bytes = base64.b64decode(clean_base64, validate=True)
            except Exception as e:
                # შიფრტექსტი აქ აღარ იბეჭდება: ის მომხმარებლის საიდუმლო მონაცემია
                raise ValueError(f"Base64 decode failed: {e}")

            # Now do AES decryption
            if len(encrypted_bytes) < 16:
                raise ValueError("Decryption error: Encrypted data is too short to contain IV.")
            try:
                decrypted = self.aes.decrypt(encrypted_bytes)
                return decrypted
            except Exception as e:
                raise ValueError(f"Decryption error: {e}")

        elif algo == "reverse":
            return self.reverse.Decrypt(encrypted_text)
        elif algo == "caser":
            return self.caser.Decrypt(encrypted_text, shift=self.prot.shift_for(password))
        else:
            raise ValueError("Unsupported decryption algorithm")


    def _extract_algo_marker(self, data: bytes):
        """
        Extracts the algorithm marker from the data.
        Data format: [core_data][--PASS--][sha256 hex of the password][--ALGO--][algorithm name]
        Returns core_pass_split (bytes before --ALGO-- including the password part) and algo_encoded (bytes after --ALGO--).
        """
        if ALGO_MARKER not in data:
            raise ValueError("Algorithm marker '--ALGO--' not found in the file.")

        core_pass_split, algo_encoded = data.rsplit(ALGO_MARKER, 1)
        return core_pass_split, algo_encoded

    def _append_trailer(self, output_path: str, password: str, algo: str):
        """
        ფაილის ბოლოში ამატებს პაროლის SHA-256 ჰეშსა და ალგორითმის სახელს.
        ეს მხოლოდ მას შემდეგ სრულდება, რაც ჩამალვა ნამდვილად წარმატებით დამთავრდა.
        """
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        with open(output_path, "ab") as f:
            f.write(PASS_MARKER)
            f.write(password_hash.encode("ascii"))
            f.write(ALGO_MARKER)
            f.write(algo.encode("utf-8"))

    @staticmethod
    def _discard_output(output_path: str, existed_before: bool):
        """
        წარუმატებელი ოპერაციის შემდეგ ნახევრად დაწერილი ფაილი არ უნდა დარჩეს.
        თუ ფაილი ოპერაციამდეც არსებობდა, ის ხელუხლებელი რჩება — მომხმარებლის
        ძველი ფაილის წაშლა ჩვენი შეცდომის გამო დაუშვებელია.
        """
        if existed_before:
            return
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass

    def encode_text_with_password(self, file_path: str, message: str, password: str, algo_label: str, output_path: str):
        """
        ჩამალავს ტექსტს ფოტოში (.png) ან აუდიოში (.mp3) და დაამატებს პაროლის ჰეშს.
        წარმატებისას აბრუნებს output_path-ს.

        შეცდომას აგდებს და აღარ ყლაპავს: ადრე ყველა შეცდომა მხოლოდ იბეჭდებოდა,
        შემდეგ კი პაროლის ჰეში მაინც ეწერებოდა ფაილს, ამიტომ წარუმატებელი ჩამალვის
        შემდეგაც კი იქმნებოდა ფაილი და ინტერფეისი "წარმატებას" აჩვენებდა.
        """
        algo = self.ui_algo_map.get(algo_label, "aes")
        extension = os.path.splitext(file_path)[1].lower()
        output_existed = os.path.exists(output_path)

        if extension not in (".png", ".mp3"):
            raise ValueError(
                f"Unsupported carrier '{extension or file_path}' for embedding text. "
                f"Use a .png image or an .mp3 audio file.")

        try:
            # Encrypt the message using the chosen algorithm and password
            encrypted_message = self._encrypt(algo, message, password)

            if extension == ".png":
                self.text_steg.encode_info(file_path, encrypted_message, output_path)
            else:
                self.audio_steg.encode_info(
                    secret_message=encrypted_message,
                    input_audio_file=file_path,
                    output_audio_file=output_path
                )

            self._append_trailer(output_path, password, algo)
        except Exception as e:
            self._discard_output(output_path, output_existed)
            print(f"[ERROR] Text embedding failed: {e}")
            raise

        print(f"[OK] Text embedded with password successfully to {output_path}")
        return output_path



    def encode_image_with_password(self, cover_image_path: str, secret_image_path: str, password: str, algo_label: str, output_path: str):
        """
        ჩამალავს ერთ ფოტოს მეორეში და დაამატებს პაროლის ჰეშს.
        წარმატებისას აბრუნებს output_path-ს, წინააღმდეგ შემთხვევაში აგდებს შეცდომას.
        """
        algo = self.ui_algo_map.get(algo_label, "aes")
        output_existed = os.path.exists(output_path)
        try:
            self.image_steg.encode_info(cover_image_path, secret_image_path, output_path)
            self._append_trailer(output_path, password, algo)
        except Exception as e:
            self._discard_output(output_path, output_existed)
            print(f"[ERROR] Image embedding failed: {e}")
            raise

        print(f"[OK] Image embedded with password successfully to {output_path}")
        return output_path



    def encode_audio_with_password(
        self,
        file_path: str,      # original (cover) audio – .mp3, .wav …
        message: str,        # text you want to hide
        password: str,       # password the user supplies
        algo_label: str,     # "Weak" | "Medium" | "Strong"  (stored only for UI)
        output_path: str     # where to save the stego‑audio
    ):
        """
        Convenience wrapper so GUI / scripts can call a dedicated
        'audio' method. Internally re‑uses encode_text_with_password,
        which already handles .mp3 in its switch‑case.
        """
        return self.encode_text_with_password(
            file_path, message, password, algo_label, output_path
        )


    def decode_with_password(self, file_path: str, password: str, data_type: str):
        """
        ამოიღებს დამალულ შიგთავსს. "text"/"audio"-სთვის აბრუნებს ტექსტს,
        "image"-სთვის კი PIL Image-ს. ვერ წაკითხვისას ბრუნდება None.
        """
        try:
            # Read the entire file content
            with open(file_path, "rb") as f:
                full_content = f.read()

            # Separate core content from password hash and algorithm label
            core_content_with_password_hash, algo_encoded = self._extract_algo_marker(full_content)
            if PASS_MARKER not in core_content_with_password_hash:
                raise ValueError("Password marker '--PASS--' not found in the file.")
            core_content, password_hash_encoded = core_content_with_password_hash.rsplit(PASS_MARKER, 1)
            try:
                password_hash = password_hash_encoded.decode("ascii")
                algo = algo_encoded.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("The password/algorithm trailer of this file is damaged.")

            # Validate password. hmac.compare_digest ადარებს მუდმივ დროში.
            expected = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if not hmac.compare_digest(expected, password_hash):
                raise ValueError("Invalid password.")

            # Decode based on data_type
            if data_type == "text":
                decoded_stego_content = self.text_steg.decode_info(file_path)
            elif data_type == "image":
                # For image in image, the hidden content itself is usually not encrypted.
                # The 'password protection' is for accessing the stego file and then extracting.
                decoded_image = self.image_steg.decode_info(file_path)
                if decoded_image is None:
                    raise ValueError("Could not extract a hidden image from this file.")
                print("[OK] Image content extracted successfully.")
                return decoded_image # RETURN DIRECTLY FOR IMAGE TYPE
            elif data_type == "audio":
                decoded_stego_content = self.audio_steg.decode_info(file_path)
            else:
                raise ValueError("Unsupported data type for decoding.")

            if not decoded_stego_content:
                raise ValueError("Could not extract steganographic content.")

            # ამოღებული შიგთავსი აღარ იბეჭდება: ის მომხმარებლის საიდუმლო მონაცემია
            decrypted_message = self._decrypt(algo, decoded_stego_content, password)
            print("[OK] Content decoded and decrypted successfully!")
            return decrypted_message

        except ValueError as ve:
            print(f"[ERROR] Decoding failed: {ve}")
            return None
        except FileNotFoundError:
            print(f"[ERROR] Decoding failed: file not found at {file_path}")
            return None
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during decoding: {e}")
            traceback.print_exc()
            return None
