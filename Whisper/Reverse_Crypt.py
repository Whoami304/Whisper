from protection import *

class ReverseCrypt(PasswordProtection):
    def __init__(self):
        super().__init__()

    def Encrypt(self, text: str) -> str:
        if not isinstance(text, str):
            raise ValueError("Text to encrypt must be a string.")
        utf8_bytes = text.encode('utf-8')
        reversed_bytes = utf8_bytes[::-1]
        return reversed_bytes.hex()

    def Decrypt(self, hex_str: str) -> str:
        """
        შეცდომისას აგდებს ValueError-ს. ადრე ბრუნდებოდა "Error: ..." სტრიქონი,
        რომელსაც გამომძახებელი ნამდვილ ტექსტად აღიქვამდა და დაზიანებული ფაილიც კი
        "წარმატებით გაშიფრულად" ჩანდა.
        """
        if not isinstance(hex_str, str):
            raise ValueError("Text to decrypt must be a string.")
        try:
            reversed_bytes = bytes.fromhex(hex_str)
        except ValueError as e:
            raise ValueError(f"Not valid hex data: {e}")
        original_bytes = reversed_bytes[::-1]
        try:
            return original_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(f"Decrypted data is not valid UTF-8 text: {e}")
