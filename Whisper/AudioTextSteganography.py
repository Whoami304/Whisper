import os
import shutil
from mutagen.id3 import ID3, COMM, ID3NoHeaderError
# , ID3NoTagsError
from steganography import Steganography, StegoError

class AudioTextSteganography(Steganography):
    def __init__(self):

        self.secret_message = ''
        self.input_audio_file = ''
        self.output_audio_file = ''

    def encode_info(self, secret_message: str, input_audio_file: str, output_audio_file: str):
        """
        წერს ტექსტს აუდიოს ID3 კომენტარში (desc='hidden_steg_text').
        წარმატებისას აბრუნებს output_audio_file-ს, წარუმატებლობისას აგდებს StegoError-ს.

        ტექსტი ინახება ისე, როგორც მოვიდა. ადრე აქ base64-ის სავალდებულო შემოწმება იდგა,
        რის გამოც არა-base64 ტექსტი (მაგ. ცეზარის შიფრის შედეგი) ჩუმად იკარგებოდა:
        ფუნქცია უბრალოდ ბრუნდებოდა, გამომძახებელი კი წარმატებას ბეჭდავდა.
        AES-ისა და reverse-ის შედეგი base64/hex-ია და ბაიტ-ბაიტ იგივე რჩება,
        ამიტომ ადრე შექმნილი ფაილები კვლავ იკითხება.
        """
        if not isinstance(secret_message, str):
            raise StegoError("Secret message must be a string.")
        if secret_message == "":
            raise StegoError("Secret message is empty, there is nothing to hide.")
        if not os.path.exists(input_audio_file):
            raise StegoError(f"Input audio file '{input_audio_file}' was not found.")

        try:
            shutil.copyfile(input_audio_file, output_audio_file)
        except OSError as e:
            raise StegoError(f"Could not create the output file: {e}")

        try:
            try:
                tags = ID3(output_audio_file)
            except ID3NoHeaderError:
                print(f"[INFO] {output_audio_file}: no ID3 header, creating a new ID3 tag.")
                tags = ID3()

            tags.delall("COMM:hidden_steg_text:eng")
            tags.add(COMM(encoding=3, lang='eng', desc='hidden_steg_text', text=secret_message))
            tags.save(output_audio_file, v1=0, v2_version=3)
        except Exception as e:
            # ნახევრად ჩაწერილი ფაილი არ უნდა დარჩეს, თორემ მომხმარებელი იფიქრებს რომ ის სწორია
            try:
                if os.path.exists(output_audio_file):
                    os.remove(output_audio_file)
            except OSError:
                pass
            raise StegoError(f"Could not write the hidden text into the audio tag: {e}")

        print(f"[OK] Message was successfully encoded into '{output_audio_file}'")
        return output_audio_file

    def decode_info(self, audio_file_path: str):
        """
        აბრუნებს დამალულ ტექსტს, ან None-ს თუ ვერაფერი იპოვა.
        ბრუნდება ზუსტად ის, რაც ჩაიწერა (მხოლოდ გარე ცარიელი სიმბოლოები იჭრება).
        """
        try:
            tags = ID3(audio_file_path)
            comment_frames = tags.getall("COMM:hidden_steg_text:eng")

            if not comment_frames:
                print("[ERROR] No 'hidden_steg_text' frame found in the ID3 tag.")
                return None

            text = comment_frames[0].text
            if not text or not isinstance(text[0], str):
                print("[ERROR] Empty or invalid text in 'hidden_steg_text'.")
                return None

            raw_message = text[0].strip()
            if not raw_message:
                print("[ERROR] The hidden text is empty.")
                return None
            return raw_message
        except Exception as e:
            print("[ERROR] Failed to read the audio file:", e)
            return None



    def Check_Content(self, audio_file_path: str) -> bool:
        try:
            tags = ID3(audio_file_path)
            comment_frames = tags.getall("COMM:hidden_steg_text:eng")
            if comment_frames and comment_frames[0].text:
                print(f"[OK] Hidden data found in {audio_file_path}")
                return True
            else:
                print(f"[INFO] No hidden data found in {audio_file_path}")
                return False
        except (ID3NoHeaderError):
            print(f"[INFO] No ID3 tag found in {audio_file_path}")
        except FileNotFoundError:
            print(f"[ERROR] File not found: {audio_file_path}")
        except Exception as e:
            print(f"[ERROR] Error checking content: {e}")
        return False
